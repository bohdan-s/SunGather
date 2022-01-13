from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from version import __version__


import logging

class export_webserver(object):
    html_body = "Pending Data Retrieval"
    def __init__(self):
        return

    # Configure Webserver
    def configure(self, config, config_inverter):
        self.webServer = HTTPServer(('', config.get('port',8080)), MyServer)
        self.t = Thread(target=self.webServer.serve_forever)
        self.t.start()
        self.config_inverter = config_inverter
        logging.info(f"Webserver: Configured")

    def publish(self, inverter):
        body = "<h3>Sungather v" + __version__ + "</h3></p><table><tr><th>Register</th><th>Value</th>"
        for register in inverter:
            body = body + f"<tr><td>{register}</td><td>{inverter.get(register)}</td></tr>"
        export_webserver.html_body = body + f"</table><p>Total {len(inverter)} registers"

        body = "</p></p><table><tr><th>Configuration</th><th>Value</th>"
        for config in self.config_inverter:
            body = body + f"<tr><td>{config}</td><td>{self.config_inverter.get(config)}</td></tr>"
        export_webserver.html_body = export_webserver.html_body + body + f"</table></p>"
        logging.info("Webserver: Content Updated")
        return

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>SunGather</title><meta http-equiv='refresh' content='15'></head>", "utf-8"))
        self.wfile.write(bytes("<body>", "utf-8"))
        self.wfile.write(bytes(export_webserver.html_body, "utf-8"))
        self.wfile.write(bytes("</table>", "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))
    def log_message(self, format, *args):
        pass
