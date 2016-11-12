import time

import numpy as np


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
