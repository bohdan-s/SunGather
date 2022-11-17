import influxdb_client
import logging
from influxdb_client.client.write_api import SYNCHRONOUS

class export_influxdb(object):
    def __init__(self):
        self.client = None
        self.write_api = None

    # Configure InfluxDB
    def configure(self, config, inverter):
        self.influxdb_config = {
            'url': config.get('url', "http://localhost:8086"),
            'token': config.get('token', None),
            'username': config.get('username', None),
            'password': config.get('password', None),
            'org': config.get('org',None),
            'bucket': config.get('bucket',None)
        }
        self.influxdb_measurements = [{}]
        self.influxdb_measurements.pop() # Remove null value from list

        if not self.influxdb_config['org'] or not self.influxdb_config['bucket'] or not (self.influxdb_config['token'] or (self.influxdb_config['username'] and self.influxdb_config['password'])):
            logging.warning(f"InfluxDB: Please check configuration")
            return False

        try:
            if self.influxdb_config['token']:
                self.client = influxdb_client.InfluxDBClient(
                    url=self.influxdb_config['url'],
                    token=self.influxdb_config['token'],
                    org=self.influxdb_config['org']
                )
            elif config.get('username',False) and config.get('password',False):
                self.client = influxdb_client.InfluxDBClient(
                    url=self.influxdb_config['url'],
                    token=f"{self.influxdb_config['username']}:{self.influxdb_config['password']}",
                    org=self.influxdb_config['org']
                )

        except Exception as err:
            logging.error(f"InfluxDB: Error: {err}")
            return False

        for measurement in config.get('measurements'):
            if not inverter.validateRegister(measurement['register']):
                logging.error(f"InfluxDB: Configured to use {measurement['register']} but not configured to scrape this register")
                return False
            self.influxdb_measurements.append(measurement)

        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        logging.info(f"InfluxDB: Configured: {self.client.url}")

        return True

    def publish(self, inverter):
        sequence = []

        for measurement in self.influxdb_measurements:
            register = measurement['register']
            if not inverter.validateLatestScrape(register):
                logging.error(f"InfluxDB: Skipped collecting data, {register} missing from last scrape")
                return False
            value = inverter.getRegisterValue(register) if type(inverter.getRegisterValue(register)) is str else float(inverter.getRegisterValue(register))
            sequence.append(influxdb_client.Point(measurement['point']).tag("inverter", inverter.getInverterModel(True)).field(register, value))

        try:
            self.write_api.write(self.influxdb_config['bucket'], self.client.org, sequence)
        except Exception as err:
            logging.error("InfluxDB: " + str(err))

        logging.info("InfluxDB: Published")

        return True
