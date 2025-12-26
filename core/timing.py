import time
from contextlib import contextmanager

@contextmanager
def timed(label: str, metrics: dict):
    start = time.time()
    yield
    metrics[label] = time.time() - start
