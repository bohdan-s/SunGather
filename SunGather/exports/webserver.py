from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from version import __version__


import logging

class export_webserver(object):
    html_body = "Pending Data Retrieval"
    metrics = ""
    def __init__(self):
        False

    # Configure Webserver
    def configure(self, config, inverter):
        try:
            self.webServer = HTTPServer(('', config.get('port',8080)), MyServer)
            self.t = Thread(target=self.webServer.serve_forever)
            self.t.daemon = True    # Make it a deamon, so if main loop ends the webserver dies
            self.t.start()
            logging.info(f"Webserver: Configured")
        except Exception as err:
            logging.error(f"Webserver: Error: {err}")
            return False
        return True

    def publish(self, inverter):
        body = "<h3>Sungather v" + __version__ + "</h3></p><table><th>Address</th><tr><th>Register</th><th>Value</th></tr>"
        metrics = ""
        for register, value in inverter.latest_scrape.items():
            body += f"<tr><td>{str(inverter.getRegisterAddress(register))}</td><td>{str(register)}</td><td>{str(value)} {str(inverter.getRegisterUnit(register))}</td></tr>"
            metrics += f"{str(register)}{{address=\"{str(inverter.getRegisterAddress(register))}\", unit=\"{str(inverter.getRegisterUnit(register))}\"}} {str(value)}\n"
        export_webserver.html_body = body + f"</table><p>Total {len(inverter.latest_scrape)} registers"
        export_webserver.metrics = metrics

        body = "</p></p><table><tr><th>Configuration</th><th>Value</th></tr>"
        for setting, value in inverter.client_config.items():
            body = body + f"<tr><td>{str(setting)}</td><td>{str(value)}</td></tr>"
        for setting, value in inverter.inverter_config.items():
            body = body + f"<tr><td>{str(setting)}</td><td>{str(value)}</td></tr>"
        export_webserver.html_body = export_webserver.html_body + body + f"</table></p>"

        return True

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes(export_webserver.metrics, "utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes("<html><head><title>SunGather</title><meta charset='UTF-8'><meta http-equiv='refresh' content='15'></head>", "utf-8"))
            self.wfile.write(bytes("<body>", "utf-8"))
            self.wfile.write(bytes(export_webserver.html_body, "utf-8"))
            self.wfile.write(bytes("</table>", "utf-8"))
            self.wfile.write(bytes("</body></html>", "utf-8"))


    def log_message(self, format, *args):
        pass
