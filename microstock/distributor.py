"""Stock Agency Contributor Direct Distribution Engine (FTP / FTPS / SFTP).

Automates batch asset delivery to Adobe Stock Contributor, Shutterstock Contributor,
and Freepik. Tracks submission logs in the local SQLite database.
"""
from __future__ import annotations

import ftplib
import os
import ssl
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import db

AGENCY_ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "adobe_stock": {
        "name": "Adobe Stock Contributor",
        "host": "sftp.contributor.adobestock.com",
        "port": 22,
        "protocol": "sftp",
        "doc_url": "https://contributor.stock.adobe.com",
    },
    "shutterstock": {
        "name": "Shutterstock Contributor",
        "host": "ftps.shutterstock.com",
        "port": 21,
        "protocol": "ftps",
        "doc_url": "https://submit.shutterstock.com",
    },
    "freepik": {
        "name": "Freepik Contributor",
        "host": "ftp.freepik.com",
        "port": 21,
        "protocol": "ftp",
        "doc_url": "https://contributor.freepik.com",
    },
}


@dataclass
class UploadResult:
    filename: str
    success: bool
    error: Optional[str] = None
    bytes_uploaded: int = 0
    duration: float = 0.0


def test_agency_connection(
    host: str,
    port: int,
    protocol: str,
    username: str,
    password: str,
    timeout: int = 10,
) -> Tuple[bool, str]:
    """Test handshake and authentication against an agency FTP/SFTP server."""
    proto = protocol.lower().strip()
    try:
        if proto in ("ftp", "ftps"):
            if proto == "ftps":
                ftps = ftplib.FTP_TLS(timeout=timeout)
                ftps.connect(host, port)
                ftps.login(username, password)
                ftps.prot_p()
                ftps.quit()
            else:
                ftp = ftplib.FTP(timeout=timeout)
                ftp.connect(host, port)
                ftp.login(username, password)
                ftp.quit()
            return True, f"Koneksi ke {host}:{port} ({proto.upper()}) berhasil."

        elif proto == "sftp":
            # Test via ssh / sftp client subprocess
            cmd = [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                "-o", f"ConnectTimeout={timeout}",
                "-p", str(port),
                f"{username}@{host}",
                "help",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if res.returncode in (0, 1):  # 0/1 means connected, help command executed or rejected
                return True, f"Koneksi SFTP ke {host}:{port} berhasil."
            return False, res.stderr.strip() or f"Koneksi SFTP ditolak (kode {res.returncode})"

        return False, f"Protokol '{protocol}' tidak didukung."
    except Exception as e:
        return False, str(e)


def upload_single_file_ftp(
    filepath: str,
    host: str,
    port: int,
    username: str,
    password: str,
    use_tls: bool = False,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    timeout: int = 60,
) -> UploadResult:
    """Upload a single file via FTP / FTPS."""
    t0 = time.time()
    filename = os.path.basename(filepath)
    if not os.path.isfile(filepath):
        return UploadResult(filename, False, "File lokal tidak ditemukan")

    file_size = os.path.getsize(filepath)
    uploaded = 0

    try:
        ftp: ftplib.FTP
        if use_tls:
            ftp = ftplib.FTP_TLS(timeout=timeout)
            ftp.connect(host, port)
            ftp.login(username, password)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP(timeout=timeout)
            ftp.connect(host, port)
            ftp.login(username, password)

        ftp.set_pasv(True)

        def _callback(chunk: bytes):
            nonlocal uploaded
            uploaded += len(chunk)
            if progress_callback:
                progress_callback(uploaded, file_size)

        with open(filepath, "rb") as f:
            ftp.storbinary(f"STOR {filename}", f, blocksize=32768, callback=_callback)

        ftp.quit()
        return UploadResult(filename, True, None, uploaded, time.time() - t0)
    except Exception as e:
        return UploadResult(filename, False, str(e), uploaded, time.time() - t0)


def dispatch_batch_to_agency(
    agency_key: str,
    file_paths: List[str],
    credentials: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[UploadResult]:
    """Upload a list of image files to a stock agency and record results in SQLite database."""
    creds = credentials or db.get_agency_account(agency_key)
    if not creds:
        raise ValueError(f"Kredensial untuk agensi '{agency_key}' belum disetel.")

    host = creds["host"]
    port = int(creds.get("port", 21))
    proto = str(creds.get("protocol", "ftp")).lower()
    user = creds["username"]
    pwd = creds["password"]
    is_tls = proto == "ftps"

    results = []
    total_files = len(file_paths)

    for idx, fpath in enumerate(file_paths, 1):
        fname = os.path.basename(fpath)
        if progress_callback:
            progress_callback(idx, total_files, f"Mengunggah ({idx}/{total_files}): {fname}")

        res = upload_single_file_ftp(
            filepath=fpath,
            host=host,
            port=port,
            username=user,
            password=pwd,
            use_tls=is_tls,
        )
        results.append(res)

        # Log to SQLite
        db.log_submission(
            agency_name=agency_key,
            submission_type=proto,
            remote_filename=fname,
            status="uploaded" if res.success else "failed",
            error_message=res.error,
        )

    return results
