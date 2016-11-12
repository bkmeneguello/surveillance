import threading


class Service(threading.Thread):
    def __init__(self):
        super().__init__()
        self.running = False

    def stop(self):
        self.running = False

    def wait_finish(self, timeout=None):
        self.join(timeout)
        if self.running:
            raise TimeoutError
