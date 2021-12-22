import logging
import requests
import datetime

# Configure PVOutput
class export_pvoutput(object):
    def __init__(self):
        self.api_key = None
        self.system_id = None
        self.status_url = "https://pvoutput.org/service/r2/addstatus.jsp"
        self.metric_mappings = None
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

    def configure(self, config):
        self.api_key = config.get('api')
        self.system_id = config.get('sid')
        self.rate_limit = config.get('rate_limit', 60)

        for parameter in config.get('parameters'):
            self.parameters.append(parameter)

        logging.info("Configured PVOutput Client")



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
        at_least_one_of = set(["v1", "v2", "v3", "v4"])

        now = datetime.datetime.strptime(inverter.get('timestamp'), "%Y-%m-%d %H:%M:%S")

        if self.latest_run:
            # Spread out our publishes over the hour based on the rate limit
            time_diff = (now - self.latest_run).total_seconds()
            if time_diff < (3600 / self.rate_limit):
                return "skipped"

        payload = {
            "d": now.strftime("%Y%m%d"),
            "t": now.strftime("%H:%M"),
        }

        value_present = False
        for parameter in self.parameters:
            if parameter.get('name') == 'v1' or parameter.get('name') == 'v2' or parameter.get('name') == 'v3' or parameter.get('name') == 'v4':
                value_present = True
            if parameter.get('register'):
                if parameter.get('multiple'):
                    payload.update({parameter.get('name'): str(inverter.get(parameter.get('register')) * parameter.get('multiple'))})
                else:
                    payload.update({parameter.get('name'): str(inverter.get(parameter.get('register')))})
            elif parameter.get('value'):
                payload.update({parameter.get('name'): parameter.get('value')})

        if not value_present:
            logging.error("PVOutput mapping failed, please review metric names and update")
            return False

        logging.debug("PVOutput Request: " + self.status_url + ", " + str(self.headers) + " : " + str(payload))
        response = requests.post(url=self.status_url, headers=self.headers, params=payload)

        if response.status_code != requests.codes.ok:
            raise RuntimeError(response.text)

        logging.info("Published to PVOutput")
        self.latest_run = now


