import logging
import time
import uuid
from threading import Condition, RLock

from src.core.exceptions import ServiceError
from src.infrastructure import task_queue

PENDING_CODE = "PENDING"
COMPLETED_CODE = "COMPLETED"
FAILED_CODE = "FAILED"
UNKNOWN_CODE = "UNKNOWN"


logger = logging.getLogger(__name__)


class JobStatusManager:
    def __init__(self, cleanup_interval: int = 300) -> None:
        self._status = {}  # {job_id: (status, result/error | None)}
        self._journal_status = {}  # {job_id: time elapsed from creation}
        self._cleanup_interval = cleanup_interval
        self._update_cleanup_time = 60  # Add 1 minute to wait for the UI
        self._last_cleanup = 0
        self._lock = RLock()

        self.th_condition = Condition(lock=self._lock)

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

                self.th_condition.notify_all()

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


def check_status(
    job_id: str,
    timeout: float = 180,
    job_manager: JobStatusManager = job_manager,
) -> tuple[str, dict | None | str]:
    """Wait until a process, with the given job_id, is finished.

    Paramters
    ---------
        - job_id (str) : job_id of the job in consideration
        - timeout (float) : after a time greater than timeout is passed from the first
            check, the process is terminated and an UNKNOWN_CODE is returned.
        - job_manager (JobStatusManager) : can be provided a different JobStatusManager
            instance in case the default one is not used. Can be usefull for testing
            or for multiprocessing.

    Returns
    -------
        A tuple containing the status code and the result from the get_status method of
        the job_manager.

    """

    start = time.time()

    th_condition = job_manager.th_condition

    with th_condition:
        while True:
            status, result = job_manager.get_status(job_id)

            if status == COMPLETED_CODE or status == FAILED_CODE:
                return status, result

            remaining_timeout = timeout - (time.time() - start)
            if remaining_timeout <= 0:
                return UNKNOWN_CODE, "timeout"

            if not th_condition.wait(timeout=remaining_timeout):
                return UNKNOWN_CODE, "timeout"


def complete_task(
    task_name: str,
    args: tuple,
    timeout: float = 180,
    job_manager: JobStatusManager = job_manager,
) -> str | dict | None:
    """Add the task to the queue and wait for its end

    Parameters
    ----------
        - taks_name (str) : Name of the task. Defined in the worker script
        - args (tuple) : tuple containing the argument. The order is defined by the
            worker script
        - timeout (float) : after a time greater than timeout is passed from the first
            check, the process is terminated and an UNKNOWN_CODE is returned.
        - job_manager (JobStatusManager) : can be provided a different JobStatusManager
            instance in case the default one is not used. Can be usefull for testing
            or for multiprocessing.

    Returns
    -------
        The result parameter is returned. It is taken from the check_status function

    """

    job_id = str(uuid.uuid4())

    job_manager.add_job(job_id)
    task_queue.add_task(task_name, job_id, args)

    status, result = check_status(job_id, timeout, job_manager)
    if status == FAILED_CODE or status == UNKNOWN_CODE:
        # we log result because in case we get unknown because of timeout, it is
        # written on result
        logger.error(f"Worker failed - job_status:{status} - job_id:{job_id} - result:{result}")
        raise ServiceError(f"Service error - job_status:{status} - result:{result}")

    return result


def update_status(
    job_id: int,
    status_code: str,
    result: str | dict | None = None,
    job_manager: JobStatusManager = job_manager,
) -> None:
    """Update the job. Used just to not use the job_manager in the worker script

    Parametes
    ---------
        - job_id (str) : id of the given job
        - status_code (str) : Can be COMPLETED or FAILED (defined above)
        - result (str or None or dict) : result of the operation. For example it
            can contain the id_user of a new added user. The default value is None
        - job_manager (JobStatusManager) : can be provided a different JobStatusManager
            instance in case the default one is not used. Can be usefull for testing
            or for multiprocessing.

    """
    job_manager.update_job(job_id, status_code, result)
