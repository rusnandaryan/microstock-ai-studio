"""Curator & Acceptance Rate Telemetry Engine.

Analyzes local SQLite database records (assets, metadata, and submission logs)
to compute acceptance rates, agency breakdown, and commercial performance insights.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from . import db, metadata


def get_curation_analytics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Compute curation acceptance rates and submission breakdown from local SQLite database."""
    assets = db.list_recent_assets(limit=1000, db_path=db_path)
    submissions = db.list_recent_submissions(limit=1000, db_path=db_path)

    total_assets = len(assets)
    total_submissions = len(submissions)

    # Agency breakdown
    agency_counts: Dict[str, int] = {}
    successful_uploads = 0
    failed_uploads = 0

    for sub in submissions:
        agency = sub.get("agency_name", "unknown")
        agency_counts[agency] = agency_counts.get(agency, 0) + 1
        status = sub.get("status", "")
        if status in ("uploaded", "submitted", "accepted"):
            successful_uploads += 1
        elif status == "failed":
            failed_uploads += 1

    upload_success_rate = (
        (successful_uploads / total_submissions * 100.0) if total_submissions > 0 else 100.0
    )

    # Category breakdown
    cat_counts: Dict[str, int] = {}
    for a in assets:
        cid = a.get("adobe_category_id", 12)
        cname = metadata.ADOBE_CATEGORIES.get(cid, "Lifestyle")
        cat_counts[cname] = cat_counts.get(cname, 0) + 1

    # Top categories sorted
    top_categories = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_assets": total_assets,
        "total_submissions": total_submissions,
        "successful_uploads": successful_uploads,
        "failed_uploads": failed_uploads,
        "upload_success_rate": round(upload_success_rate, 1),
        "agency_breakdown": agency_counts,
        "top_categories": top_categories,
    }
