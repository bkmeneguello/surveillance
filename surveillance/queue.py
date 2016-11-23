import collections
import logging
import threading

from . import stats


class Queue(object):
    def __init__(self, name, maxlen):
        self.name = name
        self.queue = collections.deque(maxlen=maxlen)
        self.lock = threading.Condition()

        self.__stats_tpl = 'queue.{}.{{}}'.format(self.name)
        self.__stats_len = self.__stats_tpl.format('len')
        self.__stats_push = self.__stats_tpl.format('push')
        self.__stats_pop = self.__stats_tpl.format('pop')
        self.__stats_peek = self.__stats_tpl.format('peek')

    def push(self, item):
        with self.lock:
            stats.incr(self.__stats_push)
            stats.gauge(self.__stats_len, len(self.queue))
            if len(self.queue) == self.queue.maxlen:
                logging.debug('queue full')
            self.queue.append(item)
            self.lock.notify()

    def pop(self, timeout=None):
        with self.lock:
            stats.incr(self.__stats_pop)
            if not self.lock.wait_for(lambda: len(self.queue), timeout):
                raise TimeoutError()
            return self.queue.popleft()

    def peek(self, timeout=None):
        with self.lock:
            stats.incr(self.__stats_peek)
            if not self.lock.wait_for(lambda: len(self.queue), timeout):
                raise TimeoutError()
            return self.queue[0]


class QueueFan(object):
    def __init__(self, *queues):
        self.queues = queues

    def push(self, item):
        for queue in self.queues:
            queue.push(item)
