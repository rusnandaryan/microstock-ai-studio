"""Enterprise Security Module: OS Keychain & Encrypted Local Vault.

Safely stores and retrieves agency SFTP credentials and Google Gemini API keys
using native macOS Keychain (via /usr/bin/security) when permitted, with an
automatic fallback to an authenticated machine-keyed Encrypted Local Vault.
Zero plaintext passwords stored in database tables or logs.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import json
import os
import platform
import shutil
import subprocess
import sys
import uuid
from typing import Any, Dict, Optional

VAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "data")
VAULT_FILE = os.path.join(VAULT_DIR, ".vault.enc")
SALT_FILE = os.path.join(VAULT_DIR, ".vault.salt")
SERVICE_PREFIX = "microstock-ai-studio"


# ==============================================================================
# 1. NATIVE OS KEYCHAIN (macOS)
# ==============================================================================

def is_keychain_supported() -> bool:
    """Check if macOS security CLI is installed."""
    return sys.platform == "darwin" and shutil.which("/usr/bin/security") is not None


def _keychain_set(service: str, account: str, secret: str) -> bool:
    """Store secret into macOS Keychain via /usr/bin/security."""
    if not is_keychain_supported():
        return False
    try:
        cmd = [
            "/usr/bin/security",
            "add-generic-password",
            "-a", account,
            "-s", f"{SERVICE_PREFIX}:{service}",
            "-w", secret,
            "-U",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return res.returncode == 0
    except Exception:
        return False


def _keychain_get(service: str, account: str) -> Optional[str]:
    """Retrieve secret from macOS Keychain via /usr/bin/security."""
    if not is_keychain_supported():
        return None
    try:
        cmd = [
            "/usr/bin/security",
            "find-generic-password",
            "-a", account,
            "-s", f"{SERVICE_PREFIX}:{service}",
            "-w",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        if res.returncode == 0 and res.stdout:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def _keychain_delete(service: str, account: str) -> bool:
    """Delete secret from macOS Keychain."""
    if not is_keychain_supported():
        return False
    try:
        cmd = [
            "/usr/bin/security",
            "delete-generic-password",
            "-a", account,
            "-s", f"{SERVICE_PREFIX}:{service}",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return res.returncode == 0
    except Exception:
        return False


# ==============================================================================
# 2. MACHINE-KEYED ENCRYPTED LOCAL VAULT (PORTABLE / SANDBOX-SAFE FALLBACK)
# ==============================================================================

def _get_machine_fingerprint() -> bytes:
    """Generate deterministic machine and user fingerprint."""
    raw = f"{uuid.getnode()}:{platform.node()}:{getpass.getuser()}:{sys.platform}"
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _get_or_create_salt() -> bytes:
    """Retrieve or create cryptographically secure local salt."""
    os.makedirs(VAULT_DIR, exist_ok=True)
    if os.path.exists(SALT_FILE):
        try:
            with open(SALT_FILE, "rb") as f:
                salt = f.read()
                if len(salt) >= 32:
                    return salt[:32]
        except Exception:
            pass
    salt = os.urandom(32)
    try:
        with open(SALT_FILE, "wb") as f:
            f.write(salt)
        if sys.platform != "win32":
            os.chmod(SALT_FILE, 0o600)
    except Exception:
        pass
    return salt


def _derive_vault_keys() -> tuple[bytes, bytes]:
    """Derive 32-byte encryption key and 32-byte HMAC key using PBKDF2-HMAC-SHA256."""
    salt = _get_or_create_salt()
    fp = _get_machine_fingerprint()
    derived = hashlib.pbkdf2_hmac("sha256", fp, salt, 100_000, dklen=64)
    enc_key = derived[:32]
    mac_key = derived[32:]
    return enc_key, mac_key


def _encrypt_payload(data: bytes, enc_key: bytes, mac_key: bytes) -> bytes:
    """Authenticated stream encryption: IV (16B) + Ciphertext + HMAC-SHA256 (32B)."""
    iv = os.urandom(16)
    # Generate keystream blocks using HMAC-SHA256 in counter mode
    ct = bytearray(len(data))
    block_idx = 0
    pos = 0
    while pos < len(data):
        ctr = block_idx.to_bytes(4, "big")
        keystream_block = hmac.new(enc_key, iv + ctr, hashlib.sha256).digest()
        chunk_len = min(len(keystream_block), len(data) - pos)
        for i in range(chunk_len):
            ct[pos + i] = data[pos + i] ^ keystream_block[i]
        pos += chunk_len
        block_idx += 1
    
    auth_tag = hmac.new(mac_key, iv + bytes(ct), hashlib.sha256).digest()
    return iv + bytes(ct) + auth_tag


def _decrypt_payload(blob: bytes, enc_key: bytes, mac_key: bytes) -> Optional[bytes]:
    """Decrypt authenticated stream and verify HMAC-SHA256 tag."""
    if len(blob) < 48:  # 16 bytes IV + 32 bytes tag
        return None
    iv = blob[:16]
    auth_tag = blob[-32:]
    ct = blob[16:-32]
    
    expected_tag = hmac.new(mac_key, iv + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(auth_tag, expected_tag):
        return None  # Tampered or corrupted vault
    
    pt = bytearray(len(ct))
    block_idx = 0
    pos = 0
    while pos < len(ct):
        ctr = block_idx.to_bytes(4, "big")
        keystream_block = hmac.new(enc_key, iv + ctr, hashlib.sha256).digest()
        chunk_len = min(len(keystream_block), len(ct) - pos)
        for i in range(chunk_len):
            pt[pos + i] = ct[pos + i] ^ keystream_block[i]
        pos += chunk_len
        block_idx += 1
    
    return bytes(pt)


def _load_vault() -> Dict[str, str]:
    """Load and decrypt dictionary from encrypted local vault file."""
    if not os.path.exists(VAULT_FILE):
        return {}
    try:
        with open(VAULT_FILE, "rb") as f:
            blob = f.read()
        enc_key, mac_key = _derive_vault_keys()
        pt = _decrypt_payload(blob, enc_key, mac_key)
        if pt is None:
            return {}
        data = json.loads(pt.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_vault(data: Dict[str, str]) -> bool:
    """Encrypt and save dictionary into local vault file with 0600 permissions."""
    try:
        os.makedirs(VAULT_DIR, exist_ok=True)
        raw_bytes = json.dumps(data).encode("utf-8")
        enc_key, mac_key = _derive_vault_keys()
        blob = _encrypt_payload(raw_bytes, enc_key, mac_key)
        with open(VAULT_FILE, "wb") as f:
            f.write(blob)
        if sys.platform != "win32":
            os.chmod(VAULT_FILE, 0o600)
        return True
    except Exception:
        return False


# ==============================================================================
# 3. UNIFIED HIGH-LEVEL CREDENTIAL API
# ==============================================================================

def store_secret(service: str, account: str, secret: str) -> bool:
    """Store secret into Keychain first, falling back transparently to Encrypted Vault."""
    if not service or not account or secret is None:
        return False
    # Attempt Keychain if supported
    if _keychain_set(service, account, secret):
        return True
    # Fallback to local encrypted vault
    vault = _load_vault()
    key = f"{service}:{account}"
    vault[key] = secret
    return _save_vault(vault)


def get_secret(service: str, account: str) -> Optional[str]:
    """Retrieve secret from Keychain first, falling back to Encrypted Vault."""
    if not service or not account:
        return None
    val = _keychain_get(service, account)
    if val is not None:
        return val
    vault = _load_vault()
    key = f"{service}:{account}"
    return vault.get(key)


def delete_secret(service: str, account: str) -> bool:
    """Delete secret from both Keychain and Encrypted Vault."""
    kc_ok = _keychain_delete(service, account)
    vault = _load_vault()
    key = f"{service}:{account}"
    if key in vault:
        del vault[key]
        _save_vault(vault)
        return True
    return kc_ok


def store_agency_password(agency_name: str, username: str, password: str) -> bool:
    """Safely store SFTP/FTP password for an agency contributor account."""
    return store_secret(f"agency_{agency_name.lower()}", username, password)


def get_agency_password(agency_name: str, username: str) -> Optional[str]:
    """Retrieve SFTP/FTP password for an agency contributor account."""
    return get_secret(f"agency_{agency_name.lower()}", username)


def delete_agency_password(agency_name: str, username: str) -> bool:
    """Delete SFTP/FTP password for an agency contributor account."""
    return delete_secret(f"agency_{agency_name.lower()}", username)


def store_gemini_api_key(api_key: str) -> bool:
    """Safely store Google Gemini API key."""
    return store_secret("google_gemini", "api_key", api_key)


def get_gemini_api_key() -> Optional[str]:
    """Retrieve Google Gemini API key from Keychain or Encrypted Vault."""
    val = get_secret("google_gemini", "api_key")
    if val:
        return val
    # Fallback to os.environ if not yet in vault
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def get_security_status() -> Dict[str, Any]:
    """Inspect active security backends and credential count."""
    vault = _load_vault()
    return {
        "keychain_supported": is_keychain_supported(),
        "vault_encrypted": os.path.exists(VAULT_FILE),
        "vault_path": VAULT_FILE,
        "total_stored_secrets": len(vault),
    }
