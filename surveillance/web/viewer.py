import gzip
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO

import pkg_resources
from PIL import Image
from jinja2 import Template

from ..service import Service


class MyHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, queues):
        super().__init__(server_address, RequestHandlerClass)
        self.queues = queues


MIMETYPE_EXT = {'png': 'image/png', 'jpg': 'image/jpeg'}
FORMAT_EXT = {'png': 'png', 'jpg': 'jpeg'}


class MyRequesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path, query = self.path.rsplit('?', 1) if '?' in self.path else (self.path, '')
        path, href = path.rsplit('#', 1) if '#' in path else (path, '')
        try:
            if path == '/':
                path = '/index.html'
            if path.startswith('/capture/') and (path.endswith(('.png', '.jpg'))):
                prefix, filename = path.rsplit('/', 1)
                queue, ext = filename.rsplit('.')

                ndarray = self.server.queues[queue].pop().ndarray
                self.send_response(200)
                enc_gz = 'gzip' in self.headers.get('Accept-Encoding', '')
                self.send_header('Content-type', MIMETYPE_EXT[ext])
                if enc_gz:
                    self.send_header('Content-Encoding', 'gzip')
                self.end_headers()
                im = Image.fromarray(ndarray)
                b = BytesIO()
                im.save(b, format=FORMAT_EXT[ext])
                im_bytes = b.getvalue()
                if enc_gz:
                    im_bytes = gzip.compress(im_bytes)
                self.wfile.write(im_bytes)
                return
            if path.endswith('.html'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                tpl = pkg_resources.resource_string('surveillance.web', path)
                tpl = Template(tpl.decode('utf-8'))
                self.wfile.write(str.encode(tpl.render(sources=self.server.queues.keys())))
                return
        except IOError:
            self.send_error(404, 'File Not Found: %s' % path)


class Viewer(Service):
    def __init__(self, queues, host='127.0.0.1', port=8080):
        super().__init__()
        self.queues = queues
        self.host = host
        self.port = port

        self.server = None

    def run(self):
        self.server = MyHTTPServer((self.host, self.port), MyRequesHandler, self.queues)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()

    def wait_finish(self, timeout=None):
        pass
