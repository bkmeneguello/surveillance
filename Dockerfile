FROM alpine:3.4

ADD dist/Surveillance-1.0-py3-none-any.whl /
RUN apk add --no-cache ffmpeg python3 python3-dev g++ &&\
    ln -s /usr/include/locale.h /usr/include/xlocale.h &&\
    pip3 install pip setuptools --no-cache-dir --upgrade &&\
    pip3 install Surveillance-1.0-py3-none-any.whl --no-cache-dir &&\
    apk del python3-dev g++

ENTRYPOINT ["python3", "-m", "surveillance"]
