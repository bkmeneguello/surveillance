import logging
import subprocess as sp
import threading

from . import stats
from .frame import Frame
from .service import Service


class Reader(Service):
    def __init__(self, name, queue, source, shape, capture_options=None, bufsize=10 ** 8):
        super().__init__()
        self.name = name
        self.queue = queue
        self.source = source
        self.shape = shape
        self.capture_options = capture_options
        self.bufsize = bufsize

        self.frames = 0
        self.frame_lock = threading.Condition()

    def run(self):
        command = ['ffmpeg'] + \
                  (self.capture_options or []) + \
                  ['-i', self.source,
                   '-f', 'image2pipe',
                   '-pix_fmt', {3: 'rgb24'}[self.shape[2]],
                   '-vcodec', 'rawvideo', '-']
        self.running = True
        pipe = None
        stats_tpl = 'capture.{}.{{}}'.format(self.name)
        stats_loop = stats_tpl.format('loop')
        stats_frame = stats_tpl.format('frame')
        stats_invalid = stats_tpl.format('invalid')
        stats_queue = stats_tpl.format('queue')
        while self.running:
            with stats.timer(stats_loop):
                raw_image = None
                if pipe is not None:
                    if pipe.poll() is None:
                        with stats.timer(stats_frame):
                            raw_image = pipe.stdout.read(self.shape[0] * self.shape[1] * self.shape[2])
                        if not raw_image:
                            logging.debug('invalid frame data')
                            stats.incr(stats_invalid)
                            continue
                    else:
                        logging.error('subprocess has died')
                        stdout, stderr = pipe.communicate()
                        if stderr:
                            logging.warning('stderr: {}', stderr)
                        if stdout:
                            logging.debug('stdout: {}', stdout)
                        pipe = None
                        continue
                else:
                    pipe = sp.Popen(command, stdout=sp.PIPE, stderr=sp.DEVNULL, bufsize=self.bufsize)
                    logging.info('recording started')
                    continue

                if raw_image:
                    try:
                        with stats.timer(stats_queue):
                            frame = Frame(self.shape, raw_image=raw_image)
                            with self.frame_lock:
                                self.queue.push(frame)
                                self.frames += 1
                                self.frame_lock.notify()
                    except ValueError:
                        logging.exception('invalid frame')
        logging.info('process terminated')
        stdout, stderr = pipe.communicate()
        if stdout:
            logging.debug('stdout: {}', stdout)
        if stderr:
            logging.debug('stderr: {}', stderr)

    def wait_first_frame(self):
        with self.frame_lock:
            return self.frame_lock.wait_for(lambda: self.frames)
