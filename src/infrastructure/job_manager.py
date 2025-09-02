import logging
import time
from threading import RLock

PENDING_CODE = "PENDING"
COMPLETED_CODE = "COMPLETED"
FAILED_CODE = "FAILED"
UNKNOWN_CODE = "UNKNOWN"


logger = logging.Logger(__name__)


class JobStatusManager:
    def __init__(self, cleanup_interval: int = 300) -> None:
        self._status = {}  # {job_id: (status, result/error | None)}
        self._journal_status = {}  # {job_id: time elapsed from creation}
        self._cleanup_interval = cleanup_interval
        self._update_cleanup_time = 60  # Add 1 minute to wait for the UI
        self._last_cleanup = 0
        self._lock = RLock()

    def add_job(self, job_id: str) -> None:
        """Add job. The job_id must be unique (use uuid)"""
        with self._lock:
            self._status[job_id] = (PENDING_CODE, None)
            self._journal_status[job_id] = time.time() + self._cleanup_interval

    def update_job(self, job_id: str, status: str, result: str | None = None) -> None:
        """Call when job completes (worker thread only)"""
        with self._lock:
            if job_id in self._status:
                self._status[job_id] = (status, result)
                self._journal_status[job_id] += self._update_cleanup_time

    def get_status(self, job_id: str) -> tuple[str, str | None]:
        """Get status of the job with the given job_id.
        This is thread safe."""
        with self._lock:
            status, result = self._status.get(job_id, (UNKNOWN_CODE, None))
            self._delete_jobs()
            return (status, result)

    def _delete_jobs(self) -> None:
        """Delete expired jobs even if pending or not read.
        It will be difficult to delete pending jobs since 5 minutes are passed
        from the creation (probably an error occoured)"""

        with self._lock:
            now = time.time()

            if now - self._last_cleanup < self._cleanup_interval:
                return

            job_del = [job_id for job_id, el_t in self._journal_status.items() if el_t < now]

            for job_id in job_del:
                del self._status[job_id]
                del self._journal_status[job_id]

            self._last_cleanup = now


job_manager = JobStatusManager()


def check_status(job_id: str, time_interval: int = 0.07) -> tuple[str, dict]:
    """Wait until the job is finished"""

    # The first time an Unknown code is returned, it is ignored. Can happen when the
    # job_id is not inserted yet in the dictionary. This should not happen anyway
    first_time = True

    while True:
        time.sleep(time_interval)

        status, result = job_manager.get_status(job_id)

        if status == PENDING_CODE:
            first_time = False
            continue

        elif status == COMPLETED_CODE:
            return COMPLETED_CODE, result

        elif status == FAILED_CODE:
            return FAILED_CODE, result

        elif status == UNKNOWN_CODE:
            # This should never happen.
            if not first_time:
                logger.error(f"The job with id {job_id} has been deleted")
                return UNKNOWN_CODE, result
            else:
                first_time = False
                continue
