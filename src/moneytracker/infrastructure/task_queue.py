from multiprocessing import Queue

# This queue will hold the tasks for our writer worker.
# It's defined in its own module to act as a singleton, ensuring
# the API and the worker access the same queue instance.
task_queue = Queue()

# TODO: Make shure this is a singleton (created a single time)


def add_task(task_name: str, job_id: str, args: tuple) -> None:
    """Add task to the queue

    Parameters
    ----------
        - task_name (str) : name of the task, defined in the worker script
        - job_id (str) : unique identifier of the job
        - args (tuple) : tuple containing the argument. The order is defined by the
            worker script

    """
    task_queue.put((task_name, job_id, args), block=True)


def get_task() -> tuple[str, str, str | None | dict]:
    """Take a task from the queue using the FIFO method

    Returns
    -------
        - task_name (str)
        - job_id (str)
        - args (tuple)
    """

    task_name, job_id, args = task_queue.get(block=True)

    return task_name, job_id, args
