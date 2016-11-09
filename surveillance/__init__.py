import collections
import logging
import os
import subprocess as sp
import threading
import time
from datetime import datetime

import numpy as np

FFMPEG_BIN = "ffmpeg"


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

    def pop(self):
        with self.lock:
            self.lock.wait_for(lambda: len(self.queue))
            return self.queue.popleft()


class QueueFan(object):
    def __init__(self, *queues):
        self.queues = queues

    def push(self, item):
        for queue in self.queues:
            queue.push(item)


class Frame(object):
    def __init__(self, shape, ndarray=None, raw_image=None):
        self.shape = shape
        if ndarray:
            self.ndarray = ndarray
        elif raw_image:
            self.ndarray = np.fromstring(raw_image, dtype='uint8')
            self.ndarray.reshape((self.shape[1], self.shape[0], self.shape[2]))
        else:
            raise ValueError('invalid frame input')
        self.time = time.time()

    def tobytes(self):
        return self.ndarray.tobytes()


class Reader(object):
    def __init__(self, queue, source, shape, capture_options=None, bufsize=10 ** 8):
        self.queue = queue
        self.source = source
        self.shape = shape
        self.capture_options = capture_options
        self.bufsize = bufsize

        self.running = False
        self.frames = 0
        self.frame_lock = threading.Condition()

    def run(self):
        command = [FFMPEG_BIN] + \
                  (self.capture_options or []) + \
                  ['-i', self.source,
                   '-f', 'image2pipe',
                   '-pix_fmt', {3: 'rgb24'}[self.shape[2]],
                   '-vcodec', 'rawvideo', '-']
        pipe = sp.Popen(command, stdout=sp.PIPE, stderr=sp.DEVNULL, bufsize=self.bufsize)
        self.running = True
        while self.running:
            raw_image = pipe.stdout.read(self.shape[0] * self.shape[1] * self.shape[2])
            if raw_image is None:
                pipe = sp.Popen(command, stdout=sp.PIPE, stderr=sp.DEVNULL, bufsize=self.bufsize)
                logging.error('closed subprocess')
                continue
            try:
                frame = Frame(self.shape, raw_image=raw_image)
                with self.frame_lock:
                    self.queue.push(frame)
                    self.frames += 1
                    self.frame_lock.notify()
            except ValueError:
                logging.exception('invalid frame')

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        return thread

    def stop(self):
        self.running = False

    def wait_first_frame(self):
        with self.frame_lock:
            return self.frame_lock.wait_for(lambda: self.frames)


class Writer(object):
    def __init__(self, queue, target, shape, fps=24, codec='mpeg2video', codec_options=None, bufsize=10 ** 8):
        self.queue = queue
        self.target = target
        self.shape = shape
        self.fps = fps
        self.codec = codec
        self.codec_options = codec_options
        self.bufsize = bufsize

        self.last_frame = None
        self.frame_time_overflow = 0
        self.frames = 0
        self.running = False

    def run(self):
        command = [FFMPEG_BIN,
                   '-y',  # (optional) overwrite output file if it exists
                   '-f', 'rawvideo',
                   '-vcodec', 'rawvideo',
                   '-s', str(self.shape[0]) + 'x' + str(self.shape[1]),  # size of one frame
                   '-pix_fmt', {3: 'rgb24'}[self.shape[2]],
                   '-r', str(self.fps),  # frames per second
                   '-i', '-'] + \
                  (self.codec_options or []) + \
                  ['-vcodec', self.codec,
                   self.target]

        frame_duration = 1 / self.fps
        pipe = sp.Popen(command, stdin=sp.PIPE, stderr=sp.PIPE, bufsize=self.bufsize)
        self.running = True
        while self.running:
            frame = self.queue.pop()
            now = frame.time
            delta = now - (self.last_frame or now) + self.frame_time_overflow
            frames_per_frame = int(delta / frame_duration)
            self.frame_time_overflow = delta - (frames_per_frame * frame_duration)
            if frames_per_frame:
                logging.debug('%d %f %f', frames_per_frame, delta / frame_duration, delta)
            else:
                logging.debug('discarded %f %f', delta / frame_duration, delta)
            for i in range(0, frames_per_frame):
                pipe.stdin.write(frame.tobytes())
                self.frames += 1
            self.last_frame = now
        pipe.communicate()

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        return thread

    def stop(self):
        self.running = False


class PeriodicWriter(object):
    def __init__(self, period, queue, target_pattern, shape, fps=24, codec='mpeg2video', codec_options=None,
                 bufsize=10 ** 8):
        self.period = period
        self.queue = queue
        self.target_pattern = target_pattern
        self.shape = shape
        self.fps = fps
        self.codec = codec
        self.codec_options = codec_options
        self.bufsize = bufsize

        self.running = False

    def run(self):
        sequence = 1
        self.running = True
        while self.running:
            target = self.target_pattern.format(now=datetime.now(), sequence=sequence)
            dirname = os.path.dirname(target)
            os.makedirs(dirname, exist_ok=True)
            writer = Writer(self.queue, target, self.shape, fps=self.fps, codec=self.codec,
                            codec_options=self.codec_options, bufsize=self.bufsize)
            writer.start()
            time.sleep(self.period)
            writer.stop()
            logging.info('new file %s', target)
            sequence += 1

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        return thread

    def stop(self):
        self.running = False
