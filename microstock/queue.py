"""Background Task & Asynchronous Worker Queue for Microstock AI Studio.

Enables non-blocking background execution for batch vision analysis,
local upscaling, database indexing, and stock distributor dispatch.
"""
from __future__ import annotations

import concurrent.futures
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class JobRecord:
    id: str
    name: str
    status: str = "pending"  # pending, running, completed, failed, cancelled
    progress: float = 0.0    # 0.0 to 1.0
    status_text: str = "Menunggu antrean..."
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class BackgroundWorkerPool:
    """Thread-safe background worker pool with job tracking and progress monitoring."""

    def __init__(self, max_workers: int = 2):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, JobRecord] = {}
        self._futures: Dict[str, concurrent.futures.Future] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        name: str,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Submit a background job and return a tracking job_id."""
        job_id = str(uuid.uuid4())[:8]
        job = JobRecord(id=job_id, name=name)

        with self._lock:
            self._jobs[job_id] = job

        def _wrapper():
            with self._lock:
                job.status = "running"
                job.status_text = "Sedang diproses..."

            def update_progress(pct: float, message: str = ""):
                with self._lock:
                    job.progress = max(0.0, min(1.0, float(pct)))
                    if message:
                        job.status_text = message

            try:
                # Pass progress callback if accepted by target function
                if "progress_callback" in fn.__code__.co_varnames:
                    kwargs["progress_callback"] = update_progress
                res = fn(*args, **kwargs)
                with self._lock:
                    job.status = "completed"
                    job.progress = 1.0
                    job.status_text = "Selesai"
                    job.result = res
                    job.completed_at = time.time()
                return res
            except Exception as e:
                with self._lock:
                    job.status = "failed"
                    job.status_text = f"Gagal: {e}"
                    job.error = str(e)
                    job.completed_at = time.time()
                raise

        future = self._executor.submit(_wrapper)
        with self._lock:
            self._futures[job_id] = future
        return job_id

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Get status snapshot of a job."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[JobRecord]:
        """List all jobs ordered by newest first."""
        with self._lock:
            sorted_jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return sorted_jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """Attempt to cancel a pending job."""
        with self._lock:
            future = self._futures.get(job_id)
            job = self._jobs.get(job_id)
            if future and job and job.status == "pending":
                cancelled = future.cancel()
                if cancelled:
                    job.status = "cancelled"
                    job.status_text = "Dibatalkan"
                    job.completed_at = time.time()
                    return True
        return False

    def shutdown(self, wait: bool = False) -> None:
        """Shutdown the executor pool."""
        self._executor.shutdown(wait=wait)


# Global singleton instance
_default_pool: Optional[BackgroundWorkerPool] = None


def get_worker_pool() -> BackgroundWorkerPool:
    """Return the global BackgroundWorkerPool singleton."""
    global _default_pool
    if _default_pool is None:
        _default_pool = BackgroundWorkerPool(max_workers=2)
    return _default_pool
