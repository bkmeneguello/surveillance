import logging
import os
import subprocess as sp
import threading
from datetime import datetime


class Writer(threading.Thread):
    def __init__(self, queue, target, fps=24, codec='mpeg2video', codec_options=None, bufsize=10 ** 8):
        super().__init__()
        self.queue = queue
        self.target = target
        self.fps = fps
        self.codec = codec
        self.codec_options = codec_options
        self.bufsize = bufsize

        self.last_frame = None
        self.frame_time_overflow = 0
        self.frames = 0
        self.running = False

    def run(self):
        frame_duration = 1 / self.fps
        pipe = None
        self.running = True
        while self.running:
            try:
                frame = self.queue.pop(timeout=1)
            except TimeoutError:
                continue

            if pipe is None:
                command = ['ffmpeg',
                           '-y',  # (optional) overwrite output file if it exists
                           '-f', 'rawvideo',
                           '-vcodec', 'rawvideo',
                           '-s', str(frame.shape[0]) + 'x' + str(frame.shape[1]),  # size of one frame
                           '-pix_fmt', {3: 'rgb24'}[frame.shape[2]],
                           '-r', str(self.fps),  # frames per second
                           '-i', '-'] + \
                          (self.codec_options or []) + \
                          ['-vcodec', self.codec,
                           self.target]
                pipe = sp.Popen(command, stdin=sp.PIPE, stderr=sp.PIPE, bufsize=self.bufsize)

            now = frame.time
            delta = now - (self.last_frame or now) + self.frame_time_overflow
            frames_per_frame = int(delta / frame_duration)
            self.frame_time_overflow = delta - (frames_per_frame * frame_duration)
            if frames_per_frame:
                logging.debug('writen frames: %d [frames span: %f, delta: %f]', frames_per_frame,
                              delta / frame_duration, delta)
            else:
                logging.debug('discarded frame [frames span: %f, delta: %f]', delta / frame_duration, delta)

            for i in range(0, frames_per_frame):
                try:
                    pipe.stdin.write(frame.tobytes())
                    self.frames += 1
                except BrokenPipeError:
                    logging.warning('writer process unavailable')
            self.last_frame = now
        logging.info('process terminated')
        stdout, stderr = pipe.communicate()
        if stdout:
            logging.debug('stdout: {}', stdout)
        if stderr:
            logging.debug('stderr: {}', stderr)

    def stop(self):
        self.running = False

    def wait_finish(self, timeout=None):
        self.join(timeout)
        if self.running:
            raise TimeoutError


class PeriodicWriter(threading.Thread):
    def __init__(self, period, queue, target_pattern, fps=24, codec='mpeg2video', codec_options=None, bufsize=10 ** 8):
        super().__init__()
        self.period = period
        self.queue = queue
        self.target_pattern = target_pattern
        self.fps = fps
        self.codec = codec
        self.codec_options = codec_options
        self.bufsize = bufsize

        self.writer = None
        self.running = False

    def run(self):
        sequence = 1
        self.running = True
        while self.running:
            target = self.target_pattern.format(now=datetime.now(), sequence=sequence)
            dirname = os.path.dirname(target)
            os.makedirs(dirname, exist_ok=True)
            self.writer = Writer(self.queue, target, fps=self.fps, codec=self.codec,
                                 codec_options=self.codec_options, bufsize=self.bufsize)
            self.writer.start()
            try:
                self.writer.wait_finish(self.period)
            except TimeoutError:
                self.writer.stop()
                logging.info('new file %s', target)
                sequence += 1

    def stop(self):
        self.running = False
        self.writer.stop()

    def wait_finish(self, timeout=None):
        self.join(timeout)
        if self.running:
            raise TimeoutError
