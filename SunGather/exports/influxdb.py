import influxdb_client
import logging
from influxdb_client.client.write_api import SYNCHRONOUS

class export_influxdb(object):
    def __init__(self):
        self._isConfigured = False
        self.client = None
        self.write_api = None
        self.bucket = None
        self.measurements = []

    # Configure InfluxDB
    def configure(self, config, config_inverter):
        
        if not config.get('token') and config.get('org') and config.get('bucket') and config.get('measurements'):
            logging.warning(f"InfluxDB: Please check configuration")
            return False
        try:
            if config.get('token', False):
                self.client = influxdb_client.InfluxDBClient(
                    url=config.get('url', 'http://localhost:8086'),
                    token=config.get('token'),
                    org=config.get('org')
                )
            elif config.get('username',False) and config.get('password',False):
                self.client = influxdb_client.InfluxDBClient(
                    url=config.get('url', 'http://localhost:8086'),
                    token=f"{config.get('username')}:{config.get('password')}",
                    org=config.get('org')
                )

        except Exception as err:
            logging.error(f"InfluxDB: Error: {err}")
            return False
        
        self.bucket=config.get('bucket')

        for measurement in config.get('measurements'):
            self.measurements.append(measurement)

        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        logging.info(f"InfluxDB: Configured: {self.client.url}")

        self._isConfigured = True
        return self._isConfigured

    def publish(self, inverter):
        if not self._isConfigured:
            logging.info("InfluxDB: Skipped, Initial Configuration Failed")
            return False

        # Setting a Standard Measurement Name and Inverter as a tag for later filtering
        # could be extended by using values from config.yaml or SerialNo or ...
        # Maybe also better switch to p=influxdb_client.Point(xxx).Tag().Field()
        sequence= f"measure1,inverter={inverter.get('device_type_code', 'unknown').replace('.','').replace('-','')} "

        for measurement in self.measurements:
            sequence += f"{measurement.get('register')}={inverter.get(measurement.get('register'),0)},"

        # remove last ","
        sequence=sequence[:-1]
        logging.debug(f'InfluxDB: Sequence; {sequence}')
        try:
            self.write_api.write(self.bucket, self.client.org, sequence)
        except Exception as err:
            logging.error("InfluxDB: " + str(err))

        logging.info("InfluxDB: Published")

        return True
