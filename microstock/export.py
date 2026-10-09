"""Microstock Export Hub: pandas DataFrames -> CSV, and the bundled ZIP."""
from __future__ import annotations

import io
import time
import zipfile
from typing import List, Optional

import pandas as pd

from . import config
from .image_generator import BatchItem, BatchSettings


def build_metadata_dataframe(items: List[BatchItem], s: Optional[BatchSettings] = None) -> pd.DataFrame:
    """Master metadata table – one row per successfully processed image."""
    rows = []
    for it in items:
        if not it.ok:
            continue
        md = it.metadata
        rows.append({
            "Filename": it.filename,
            "Title": md.title if md else "",
            "Description": md.description if md else "",
            "Keywords": md.keywords_csv if md else "",
            "Keyword Count": len(md.keywords) if md else 0,
            "Adobe Category": md.adobe_category if md else "",
            "Adobe Category Name": md.adobe_category_name if md else "",
            "Shutterstock Categories": ",".join(md.shutterstock_categories) if md else "",
            "Style": s.style_name if s else "AI Stock",
            "Aspect Ratio": s.aspect_ratio if s else "Original",
            "Resolution": f"{it.width}x{it.height} ({(it.width * it.height) / 1_000_000:.1f} MP)",
            "AI Generated": "Yes",
            "Prompt": it.final_prompt.replace("\n", " ") if it.final_prompt else "",
        })
    return pd.DataFrame(rows)


def to_adobe_stock_df(master: pd.DataFrame) -> pd.DataFrame:
    """Adobe Stock contributor CSV: Filename, Title, Keywords, Category, Releases."""
    if master.empty:
        return pd.DataFrame(columns=["Filename", "Title", "Keywords", "Category", "Releases"])
    return pd.DataFrame({
        "Filename": master["Filename"],
        "Title": master["Title"],
        "Keywords": master["Keywords"],
        "Category": master["Adobe Category"],
        "Releases": "",
    })


def to_shutterstock_df(master: pd.DataFrame, items: List[BatchItem], s: Optional[BatchSettings] = None) -> pd.DataFrame:
    """Shutterstock CSV: Filename, Description, Keywords, Categories, Editorial,
    Mature content, illustration."""
    cols = ["Filename", "Description", "Keywords", "Categories",
            "Editorial", "Mature content", "illustration"]
    if master.empty:
        return pd.DataFrame(columns=cols)
    is_illu = "yes" if s and s.style_name in config.STYLES and config.STYLES[s.style_name].is_illustration else "no"
    return pd.DataFrame({
        "Filename": master["Filename"],
        "Description": master["Description"].where(master["Description"] != "", master["Title"]),
        "Keywords": master["Keywords"],
        "Categories": master["Shutterstock Categories"],
        "Editorial": "no",
        "Mature content": "no",
        "illustration": is_illu,
    })


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """UTF-8 with BOM so Excel opens non-ASCII correctly; standard comma CSV."""
    return df.to_csv(index=False).encode("utf-8-sig")


def build_zip(items: List[BatchItem], s: BatchSettings,
              master: Optional[pd.DataFrame] = None) -> bytes:
    """Package full-res images + metadata.csv + platform-specific CSVs."""
    master = master if master is not None else build_metadata_dataframe(items, s)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for it in items:
            if it.ok:
                # JPEG/PNG are already compressed – store, don't deflate (much faster)
                zf.writestr(it.filename, it.image_bytes, compress_type=zipfile.ZIP_STORED)
        zf.writestr("metadata.csv", dataframe_to_csv_bytes(master),
                    compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("adobe_stock.csv", dataframe_to_csv_bytes(to_adobe_stock_df(master)),
                    compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("shutterstock.csv",
                    dataframe_to_csv_bytes(to_shutterstock_df(master, items, s)),
                    compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("README.txt", _readme(s, master), compress_type=zipfile.ZIP_DEFLATED)
    return buf.getvalue()


def zip_filename(s: BatchSettings) -> str:
    return f"{s.file_prefix}-batch-{time.strftime('%Y%m%d-%H%M%S')}.zip"


def _readme(s: Optional[BatchSettings], master: pd.DataFrame) -> str:
    style_text = s.style_name if s else "Commercial AI Stock"
    ratio_text = s.aspect_ratio if s else "Original"
    model_text = s.image_model if s else "Gemini Nano Banana"
    return (
        "Microstock Magic Studio – Export Bundle\n"
        "======================================\n\n"
        f"Total Images  : {len(master)}\n"
        f"Aesthetic     : {style_text}\n"
        f"Aspect Ratio  : {ratio_text}\n"
        f"Engine        : {model_text}\n\n"
        "Included Files\n"
        "--------------\n"
        "metadata.csv     – Master sheet (Title, Description, 50 Keywords, Categories)\n"
        "adobe_stock.csv  – Direct upload for Adobe Stock Contributor (Upload CSV)\n"
        "shutterstock.csv – Direct upload for Shutterstock Contributor (Upload CSV)\n\n"
        "IMPORTANT: When uploading to stock agencies, remember to tick 'Created using AI / Generative AI'.\n"
    )
