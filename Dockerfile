FROM alpine:3.4

RUN apk add --no-cache ffmpeg python3 python3-dev g++ tzdata &&\
    ln -s /usr/include/locale.h /usr/include/xlocale.h &&\
    pip3 install pip setuptools wheel --no-cache-dir --upgrade
RUN apk add --no-cache zlib-dev jpeg-dev
COPY . /build/
RUN cd build && python3 setup.py bdist_wheel &&\
    pip3 install dist/surveillance-1.0-py3-none-any.whl --no-cache-dir &&\
    rm -r /build
RUN apk del python3-dev g++ zlib-dev jpeg-dev

ENTRYPOINT ["python3", "-m", "surveillance"]
