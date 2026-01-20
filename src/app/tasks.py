import time

from rq import get_current_job


def example(seconds):
    print("Starting task")
    for i in range(seconds):
        print(i)
        time.sleep(1)
    print("task completed")
