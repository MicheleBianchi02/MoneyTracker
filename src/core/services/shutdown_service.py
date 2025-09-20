from infrastructure.task_queue import task_queue
from infrastructure.worker import END_WORKER_TASK_NAME


def shutdown() -> None:
    job_id = "ENDING"
    task_queue.put((END_WORKER_TASK_NAME, job_id, ()), block=True)

    # TODO: Add closing db connection. Problem is that we need to wait until the
    # worker thread ended before closing all connections

    # connection_pool.close_all()
