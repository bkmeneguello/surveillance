import time
from io import BytesIO

import numpy as np
from PIL import Image


class Frame(object):
    def __init__(self, shape, ndarray=None, raw_image=None, im=None):
        self.shape = shape
        if ndarray:
            self.ndarray = ndarray
        elif raw_image:
            self.ndarray = np.fromstring(raw_image, dtype='uint8')
            self.ndarray = self.ndarray.reshape((self.shape[1], self.shape[0], self.shape[2]))
        elif im:
            self.ndarray = np.asarray(im)
        else:
            raise ValueError('invalid frame input')
        self.time = time.time()

    def tobytes(self, format=None):
        if format is None:
            return self.ndarray.tobytes()
        else:
            b = BytesIO()
            self.toimage().save(b, format=format)
            return b.getvalue()

    def toimage(self):
        return Image.fromarray(self.ndarray)
