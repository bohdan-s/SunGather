from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from threading import Thread
from version import __version__


import logging

class export_jsonserver(object):
    html_body = "Pending Data Retrieval"
    def __init__(self):
        False

    # Configure Webserver
    def configure(self, config, inverter):
        try:
            self.webServer = HTTPServer(('', config.get('port',8082)), MyServer)
            self.t = Thread(target=self.webServer.serve_forever)
            self.t.daemon = True    # Make it a deamon, so if main loop ends the webserver dies
            self.t.start()
            logging.info(f"JSON-Export: Configured")
        except Exception as err:
            logging.error(f"JSON-Export: Error: {err}")
            return False
        return True

    def publish(self, inverter):
        json_cache={"registers":{}, "client_config":{}, "inverter_config":{}}

        for register, value in inverter.latest_scrape.items():
            json_cache["registers"][str(inverter.getRegisterAddress(register))]={"register": str(register), "value":str(value), "unit": str(inverter.getRegisterUnit(register))}

        # Client Config
        for setting, value in inverter.client_config.items():
            json_cache["client_config"][str(setting)]=str(value)

        # Inverter Config
        for setting, value in inverter.inverter_config.items():
            json_cache["inverter_config"][str(setting)]=str(value)
            
        export_jsonserver.html_body = json.dumps(json_cache)
        return True

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(export_jsonserver.html_body, "utf-8"))
    def log_message(self, format, *args):
        pass
