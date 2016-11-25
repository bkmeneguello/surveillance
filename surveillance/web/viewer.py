import gzip
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

import pkg_resources
from jinja2 import Template

from .. import stats
from ..frame import Frame
from ..service import Service


class MyHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, viewer):
        super().__init__(server_address, RequestHandlerClass)
        self.viewer = viewer


MIMETYPE_EXT = {'png': 'image/png', 'jpg': 'image/jpeg'}
FORMAT_EXT = {'png': 'png', 'jpg': 'jpeg'}


def parse_rational(value):
    if value.isdigit():
        return int(value)
    elif '/' in value:
        dividend, divisor = value.split('/', 1)
        if dividend.isdigit() and divisor.isdigit():
            return int(dividend) / int(divisor)


class MyRequesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        with stats.timer(self.server.viewer.stats_response):
            path = urllib.parse.unquote(self.path)
            path, query = path.rsplit('?', 1) if '?' in path else (path, '')
            if query:
                query = dict((option.split('=') if '=' in option else (option, None)) for option in query.split('&'))
            else:
                query = {}
            path, href = path.rsplit('#', 1) if '#' in path else (path, '')
            try:
                if path == '/':
                    path = '/index.html'
                if path.startswith('/capture/') and (path.endswith(('.png', '.jpg'))):
                    prefix, filename = path.rsplit('/', 1)
                    queue, ext = filename.rsplit('.')

                    frame = self.server.viewer.queues[queue].peek()
                    self.send_response(200)
                    enc_gz = 'gzip' in self.headers.get('Accept-Encoding', '')
                    self.send_header('Content-type', MIMETYPE_EXT[ext])
                    if enc_gz:
                        self.send_header('Content-Encoding', 'gzip')
                    self.end_headers()
                    scale = parse_rational(query.get('scale', '1').strip())
                    if scale != 1:
                        shape = [int(frame.shape[0] * scale), int(frame.shape[1] * scale), frame.shape[2]]
                        with stats.timer(self.server.viewer.stats_scale):
                            frame = Frame(shape, im=frame.toimage().resize((shape[0], shape[1])))
                    with stats.timer(self.server.viewer.stats_format):
                        im_bytes = frame.tobytes(format=FORMAT_EXT[ext])
                    if enc_gz:
                        with stats.timer(self.server.viewer.stats_compress):
                            im_bytes = gzip.compress(im_bytes)
                    with stats.timer(self.server.viewer.stats_write):
                        self.wfile.write(im_bytes)
                    return
                if path.endswith('.html'):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    tpl = pkg_resources.resource_string('surveillance.web', path)
                    tpl = Template(tpl.decode('utf-8'))
                    self.wfile.write(str.encode(tpl.render(sources=self.server.viewer.queues.keys())))
                    return
            except IOError:
                self.send_error(404, 'File Not Found: %s' % path)


class Viewer(Service):
    def __init__(self, name, queues, host='127.0.0.1', port=8080):
        super().__init__()
        self.name = name
        self.queues = queues
        self.host = host
        self.port = port

        self.server = None

        self.__stats_tpl = 'viewer.{}.{{}}'.format(self.name)
        self.stats_response = self.__stats_tpl.format('response')
        self.stats_scale = self.__stats_tpl.format('scale')
        self.stats_format = self.__stats_tpl.format('format')
        self.stats_compress = self.__stats_tpl.format('compress')
        self.stats_write = self.__stats_tpl.format('write')

    def run(self):
        self.server = MyHTTPServer((self.host, self.port), MyRequesHandler, self)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()

    def wait_finish(self, timeout=None):
        pass
