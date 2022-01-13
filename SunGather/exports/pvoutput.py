import logging
import requests
import datetime

# Configure PVOutput
class export_pvoutput(object):
    def __init__(self):
        self.api_key = None
        self.system_id = None
        self.statusbatch_url = "https://pvoutput.org/service/r2/addbatchstatus.jsp"
        self.rate_limit = None
        self.parameters = []
        self.latest_run = None

    @property
    def headers(self):
        return {
            "X-Pvoutput-Apikey": self.api_key,
            "X-Pvoutput-SystemId": self.system_id,
            "Content-Type": "application/x-www-form-urlencoded",
            "cache-control": "no-cache",
        }

    def configure(self, config, config_inverter):
        self.api_key = config.get('api')
        self.system_id = config.get('sid')
        self.rate_limit = config.get('rate_limit', 60)
        self.status_interval = config.get('status_interval',5)
        self.batch_points = config.get('batch_points',1)
        self.inverter_data = { "v1": 0, "v2": 0, "v3": 0, "v4": 0, "v5": 0, "v6": 0, "v7": 0, "v8": 0, "v9": 0, "v10": 0, "v11": 0, "v12": 0 }
        self.inverter_data_count = 0
        self.payload_data = None
        self.batch_count = 0
        self.payload_format = "{date},{time},{v1},{v2},{v3},{v4},{v5},{v6},{v7},{v8},{v9},{v10},{v11},{v12}"

        for parameter in config.get('parameters'):
            self.parameters.append(parameter)

        if not (self.status_interval == 5 or self.status_interval == 10 or self.status_interval == 15):
            logging.warning("Status Invterval is invalid, valid options are 5, 10 and 15 minutes")
            return False

        logging.info("PVOutput: Configured")

    def publish(self, inverter):
        """
        See: https://pvoutput.org/help/api_specification.html#add-status-service
        Parameter   Field               Required    Format      Unit    Example     Donation
        d           Output Date         Yes         yyyymmdd    date    20210228
        t           Time                Yes         hh:mm       time    14:00   
        v1          Energy Generation   No          number      wh      10000
        v2          Power Generation    No          number      watts   2000
        v3          Energy Consumption  No          number      wh      10000
        v4          Power Consumption   No          number      watts   2000
        # At least one of the values v1, v2, v3 or v4 must be present.
        v5          Temperature         No          decimal     celsius 23.4
        v6          Voltage             No          decimal     volts   239.2
        c1          Cumulative Flag     No          number              1
        # 1 - Both v1 and v3 values are lifetime energy values. Consumption and generation energy is reset to 0 at the start of the day.
        # 2 - Only v1 generation is a lifetime energy value.
        # 3 - Only v3 consumption is a lifetime energy value.
        n           Net Flag            No          number              1
        # n parameter when set to 1 will indicate that the power values passed are net export/import rather than gross generation/consumption. This option is used for devices that are unable to report gross consumption data. The provided import/export data is merged with existing generation data to derive consumption.	
        v7          Extended Value v7   No          number      User Defined    Yes
        v8          Extended Value v8   No          number      User Defined    Yes
        v9          Extended Value v9   No          number      User Defined    Yes
        v10         Extended Value v10  No          number      User Defined    Yes
        v11         Extended Value v11  No          number      User Defined    Yes
        v12         Extended Value v12  No          number      User Defined    Yes
        m1          Text Message 1      No          text        30 chars max    Yes
        """

        now = datetime.datetime.strptime(inverter.get('timestamp'), "%Y-%m-%d %H:%M:%S")
        if not self.latest_run:     # Set last run to 1 min ago if never run, that way we don't miss any uploads
            self.latest_run = now - datetime.timedelta(minutes=1)

        # Add new data to old data and increase count of data points
        for parameter in self.parameters:
            if parameter.get('name')[0] == 'v':
                if inverter.get(parameter.get('register')):
                    if parameter.get('multiple'):
                        self.inverter_data[parameter.get('name')] = round(self.inverter_data[parameter.get('name')] + (inverter.get(parameter.get('register')) * parameter.get('multiple')),3)
                    else:
                        self.inverter_data[parameter.get('name')] = round(self.inverter_data[parameter.get('name')] + inverter.get(parameter.get('register')),3)
                else:
                    logging.warning(f"PVOutput: {parameter.get('name')} configured to use {parameter.get('register')} but inverter is not returning this register")
            elif parameter.get('name') == 'c1':
                c1 = parameter.get('value')
        self.inverter_data_count +=1
        logging.info('PVOutput: Data logged')
        logging.debug(f'PVOutput: Points: {self.batch_count} Data: {self.inverter_data}, c1={str(c1)}')

        # Process data points every status_interval
        if int(now.strftime("%M")) % self.status_interval == 0 and not now.strftime("%H:%M") == self.latest_run.strftime("%H:%M"):
            for v in self.inverter_data:
                if not self.inverter_data[v] == 0:
                    self.inverter_data[v] = round(self.inverter_data[v] / self.inverter_data_count, 2)
            self.inverter_data_count = 0

            payload = self.payload_format
            payload = payload.replace('{date}',now.strftime("%Y%m%d"))
            payload = payload.replace('{time}',now.strftime("%H:%M"))

            for data in self.inverter_data:
                payload = payload.replace('{' + data + '}',str(self.inverter_data.get(data)))

            self.inverter_data = { "v1": 0, "v2": 0, "v3": 0, "v4": 0, "v5": 0, "v6": 0, "v7": 0, "v8": 0, "v9": 0, "v10": 0, "v11": 0, "v12": 0 }

            if self.payload_data:
                self.payload_data = self.payload_data + ";"
            else: 
                self.payload_data = ""
            self.payload_data = self.payload_data + payload

            self.batch_count +=1

            if self.batch_count == self.batch_points:
                payload = {'data': self.payload_data, 'c1': str(c1)}
                logging.debug("PVOutput: Request; " + self.statusbatch_url + ", " + str(self.headers) + " : " + str(payload))
                response = requests.post(url=self.statusbatch_url, headers=self.headers, params=payload)
                self.batch_count = 0

                if response.status_code != requests.codes.ok:
                    raise RuntimeError(response.text)
                else:
                    self.payload_data = None
                    logging.info("PVOutput: Data uploaded")
            else:
                logging.info("PVOutput: Data added to next batch upload")

        self.latest_run = now


