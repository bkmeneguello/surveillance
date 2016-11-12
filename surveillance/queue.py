import collections
import logging
import threading


class Queue(object):
    def __init__(self, maxlen):
        self.queue = collections.deque(maxlen=maxlen)
        self.lock = threading.Condition()

    def push(self, item):
        with self.lock:
            if len(self.queue) == self.queue.maxlen:
                logging.debug('queue full')
            self.queue.append(item)
            self.lock.notify()

    def pop(self, timeout=None):
        with self.lock:
            if not self.lock.wait_for(lambda: len(self.queue), timeout):
                raise TimeoutError()
            return self.queue.popleft()


class QueueFan(object):
    def __init__(self, *queues):
        self.queues = queues

    def push(self, item):
        for queue in self.queues:
            queue.push(item)
