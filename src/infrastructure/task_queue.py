from multiprocessing import Queue

# This queue will hold the tasks for our writer worker.
# It's defined in its own module to act as a singleton, ensuring
# the API and the worker access the same queue instance.
task_queue = Queue()
