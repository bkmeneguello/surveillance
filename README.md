Surveillance
============

It's a simple camera surveillance system designed to effectivelly capture and store from various input sources.

### Build

Using Docker is very simple to setup the surveillance sytem, just do:
```
$ docker build -t surveillance https://github.com/bkmeneguello/surveillance.git
```
and you are ready to go!

### Configure

The configuration file is a YAML (PyYAML) with object instantiation.

This is an example of RTSP capture and basic AVI storage:
```
services:
  - !!python/object/apply:surveillance.Reader
    args: [&Q !!python/object/apply:surveillance.Queue [100], 'rtsp://192.168.0.10:554/stream=0.sdp', [1280, 720, 3]]
  - !!python/object/apply:surveillance.PeriodicWriter
    args: [60, *Q, '/surveillance/garden/{now:%Y-%m-%d_%H:%M:%S}.avi']
    kwds: {codec: 'h264', codec_options: ['-threads', '4', '-preset', 'medium', '-crf', '35', '-tune', 'stillimage', '-movflags', '+faststart']}
```

To use an USB camera, this is a setup example:
```
services:
  - !!python/object/apply:surveillance.Reader
    args: [&Q !!python/object/apply:surveillance.Queue [100], '/dev/video0', [640, 480, 3]]
    kwds: {capture_options: ['-f', 'v4l2', '-video_size', '640x480']}
  - !!python/object/apply:surveillance.PeriodicWriter
    args: [60, *Q, 'cam/desk{now:%Y-%m-%d_%H:%M:%S}.avi']
    kwds: {codec: 'h264', codec_options: ['-threads', '4', '-preset', 'medium', '-crf', '35', '-tune', 'stillimage', '-movflags', '+faststart']}
```

- More info about this syntax in [PyYAML site](http://pyyaml.org/wiki/PyYAMLDocumentation#YAMLsyntax)
- More info about codecs and capture/encode options in [ffmpeg site](https://www.ffmpeg.org/ffmpeg.html)

### Run

```
$ docker run -d -v `pwd`/surveillance.conf:/etc/surveillance.conf:ro \
                -v `pwd`/surveillance:/surveillance \
                -v /etc/localtime:/etc/localtime:ro \
                --device /dev/video0 \
                --name surveillance \
                -e TZ=America/Sao_Paulo \
                surveillance -l -
```
Notice the _device_ option to allow non-privileged containers to access your host's camera device. It's only useful to USB camera capture.  