import logging
import requests
import datetime
import time

# Configure PVOutput
class export_pvoutput(object):
    def __init__(self):
        self._isConfigured = False
        self.api_key = None
        self.system_id = None
        self.url_base = "https://pvoutput.org/service/r2/"
        self.url_addbatchstatus = self.url_base + "addbatchstatus.jsp"
        self.url_jointeam = self.url_base + "jointeam.jsp"
        self.url_leaveteam = self.url_base + "leaveteam.jsp"
        self.url_getsystem = self.url_base + "getsystem.jsp"
        self.rate_limit = None
        self.parameters = []
        self.last_run = None
        self.tid = '1618'

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
        self.collected_data = {}
        self.payload_data = None
        self.batch_count = 0
        self.last_run = 0

        for parameter in config.get('parameters'):
            self.parameters.append(parameter)
        try:
            logging.debug(f"PVOutput: Get System ; {self.url_getsystem}, {str(self.headers)}, 'teams': '1'")
            response = requests.post(url=self.url_getsystem,headers=self.headers, params={'teams': '1'}, timeout=3)
            logging.debug(f"PVOutput: Response; {str(response.status_code)} Message; {str(response.content)}")

            if response.status_code == 200:
                system = response.text.split(';')[0]
                teams = response.text.split(';')[2]

                invertername = system.split(',')[0]
                self.status_interval = int(system.split(',')[15])

                team_member = False
                for team in teams.split(','):
                    if team == self.tid:
                        team_member = True
            else:
                logging.error(f"PVOutput: System Status Failed; {str(response.status_code)} Message; {str(response.content)}")
        
        except Exception as err:
            logging.error(f"PVOutput: Failed to configure")
            logging.debug(f"{err}")
            return False

        try:
            join_team = config.get('join_team',True)
            if not team_member and join_team:
                logging.debug(f"PVOutput: Join Team; {self.url_jointeam}, {str(self.headers)}, 'tid': '{self.tid}'")
                response = requests.post(url=self.url_jointeam,headers=self.headers, params={'tid': self.tid}, timeout=3)
                logging.debug(f"PVOutput: Response; {str(response.status_code)} Message; {str(response.content)}")
            elif team_member and not join_team:
                logging.debug(f"PVOutput: Leave Team; {self.url_leaveteam}, {str(self.headers)}, 'tid': '{self.tid}'")
                response = requests.post(url=self.url_leaveteam,headers=self.headers, params={'tid': self.tid}, timeout=3)
                logging.debug(f"PVOutput: Response; {str(response.status_code)} Message; {str(response.content)}")  
        except Exception as err:
            logging.debug(f"{err}")

        logging.info(f"PVOutput: Configured export to {invertername} every {self.status_interval} minutes")
        return True

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

        # Check all required registers have been returned by the inverter
        if not inverter.get('timestamp', False):
            logging.warning('PVOutput: Skipping, Timestamp missing from last scrape')
            return False
        for parameter in self.parameters:
            if parameter.get('name')[0] == 'v':
                if not inverter.get(parameter.get('register', False)):
                    logging.warning(f"PVOutput: Skipping, {parameter.get('name')} configured to use {parameter.get('register')} but inverter is not returning this register")
                    return False

        now = datetime.datetime.strptime(inverter.get('timestamp'), "%Y-%m-%d %H:%M:%S")

        # Add new data to old data and increase count of data points
        for parameter in self.parameters:
            if parameter.get('name')[0] == 'v':                    
                if self.collected_data.get(parameter.get('name'),False):
                        if parameter.get('multiple'):
                            self.collected_data[parameter.get('name')] = round(self.collected_data[parameter.get('name')] + (inverter.get(parameter.get('register')) * parameter.get('multiple')),3)
                        else:
                            self.collected_data[parameter.get('name')] = round(self.collected_data[parameter.get('name')] + inverter.get(parameter.get('register')),3)
                else:
                        if parameter.get('multiple'):
                            self.collected_data[parameter.get('name')] = round(inverter.get(parameter.get('register')) * parameter.get('multiple'),3)
                        else:
                            self.collected_data[parameter.get('name')] = inverter.get(parameter.get('register'))
            elif parameter.get('name') == 'c1':
                cumulative_energy = parameter.get('value')

        if self.collected_data.get('count',False):
            self.collected_data['count'] +=1
        else:
            self.collected_data['count'] = 1

        logging.debug(f'PVOutput: Data Logged: {self.collected_data}')

        # Process data points every status_interval
        if((time.time() - self.last_run) > (self.status_interval * 60)):
            for v in self.collected_data:
                if v[0] == 'v' and not self.collected_data[v] == 0:
                    if v[1] == '6' or v[1] == '7':  # Round to 1 decimal place
                        self.collected_data[v] = round(self.collected_data[v] / self.collected_data['count'], 1)
                    else:   # Getting errors when uploading decimals for power/energy so return INT
                        self.collected_data[v] = int((self.collected_data[v] / self.collected_data['count']))

            data_point = str(now.strftime("%Y%m%d")) + "," + str(now.strftime("%H:%M"))

            for x in range(1, 13):
                v = 'v' + str(x)
                if self.collected_data.get(v):
                   data_point = data_point + "," + str(self.collected_data[v])
                else:
                    data_point = data_point + ","

            self.collected_data = {}

            if self.payload_data:
                self.payload_data = self.payload_data + ";"
            else: 
                self.payload_data = ""

            self.payload_data = self.payload_data + data_point

            self.batch_count +=1
            
            if self.batch_count >= self.batch_points:
                payload = {}
                payload['data'] = self.payload_data

                if 'cumulative_energy' in locals():
                    payload['c1'] = cumulative_energy

                try:
                    logging.debug("PVOutput: Request; " + self.url_addbatchstatus + ", " + str(self.headers) + " : " + str(payload))
                    response = requests.post(url=self.url_addbatchstatus, headers=self.headers, params=payload, timeout=3)
                    self.batch_count = 0

                    if response.status_code != requests.codes.ok:
                        logging.error(f"PVOutput: Upload Failed; {str(response.status_code)} Message; {str(response.content)}")
                    else:
                        self.payload_data = None
                        logging.info("PVOutput: Data uploaded")
                except Exception as err:
                    logging.error(f"PVOutput: Failed to Upload")
                    logging.debug(f"{err}")
            else:
                logging.info("PVOutput: Data added to next batch upload")

        self.last_run = time.time()