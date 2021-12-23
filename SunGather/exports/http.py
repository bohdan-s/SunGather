from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread

import logging

class export_http(object):
    html_body = "Pending Data retrieval"
    def __init__(self):
        return

    # Configure HTTP
    def configure(self, config):
        self.webServer = HTTPServer(('localhost', config.get('port',8080)), MyServer)
        t = Thread(target=self.webServer.serve_forever)
        t.start()
        logging.info("Configured Simple HTTP Server")

    def publish(self, inverter):
        #global html_body

        body = "<table><tr><th>Register</th><th>Value</th>"
        for register in inverter:
            body = body + f"<tr><td>{register}</td><td>{inverter.get(register)}</td></tr>"
        export_http.html_body = body + f"</table><p>Total {len(inverter)} registers"
        print("Publish HTTP")
        return

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>SunGather</title><meta http-equiv='refresh' content='15'></head>", "utf-8"))
        self.wfile.write(bytes("<body>", "utf-8"))
        self.wfile.write(bytes(export_http.html_body, "utf-8"))
        self.wfile.write(bytes("</table>", "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))
    def log_message(self, format, *args):
        pass
