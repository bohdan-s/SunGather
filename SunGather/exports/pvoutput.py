import logging
import requests
import datetime
import time

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
class export_pvoutput(object):
    def __init__(self):
        self.url_base = "https://pvoutput.org/service/r2/"
        self.url_addbatchstatus = self.url_base + "addbatchstatus.jsp"
        self.url_jointeam = self.url_base + "jointeam.jsp"
        self.url_leaveteam = self.url_base + "leaveteam.jsp"
        self.url_getsystem = self.url_base + "getsystem.jsp"
        self.tid = '1618'
        self.status_interval = 5

    @property
    def headers(self):
        return {
            "X-Pvoutput-Apikey": self.pvoutput_config['api'],
            "X-Pvoutput-SystemId": self.pvoutput_config['sid'],
            "Content-Type": "application/x-www-form-urlencoded",
            "cache-control": "no-cache",
        }

    def configure(self, config, inverter):
        self.pvoutput_config = {
            'api': config.get('api', None),
            'sid': config.get('sid', None),
            'join_team': config.get('join_team', True),
            'rate_limit': config.get('rate_limit', 60),
            'cumulative_flag': config.get('cumulative_flag',0),
            'batch_points': config.get('batch_points',1)
        }
        self.pvoutput_parameters = [{}]
        self.pvoutput_parameters.pop() # Remove null value from list

        self.collected_data = {}
        self.batch_data = []
        self.batch_count = 0
        self.last_run = 0
        self.last_publish = 0
        
        for parameter in config.get('parameters'):
            if not inverter.validateRegister(parameter['register']):
                logging.error(f"PVOutput: Configured to use {parameter['register']} but not configured to scrape this register")
                return False
            self.pvoutput_parameters.append(parameter)

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
                        break
            else:
                logging.error(f"PVOutput: System Status Failed; {str(response.status_code)} Message; {str(response.content)}")
        
        except Exception as err:
            logging.error(f"PVOutput: Failed to configure")
            logging.debug(f"{err}")
            return False

        try:
            if not team_member and self.pvoutput_config['join_team']:
                logging.debug(f"PVOutput: Join Team; {self.url_jointeam}, {str(self.headers)}, 'tid': '{self.tid}'")
                response = requests.post(url=self.url_jointeam,headers=self.headers, params={'tid': self.tid}, timeout=3)
                logging.debug(f"PVOutput: Response; {str(response.status_code)} Message; {str(response.content)}")
            elif team_member and not self.pvoutput_config['join_team']:
                logging.debug(f"PVOutput: Leave Team; {self.url_leaveteam}, {str(self.headers)}, 'tid': '{self.tid}'")
                response = requests.post(url=self.url_leaveteam,headers=self.headers, params={'tid': self.tid}, timeout=3)
                logging.debug(f"PVOutput: Response; {str(response.status_code)} Message; {str(response.content)}")  
        except Exception as err:
            pass

        logging.info(f"PVOutput: Configured export to {invertername} every {self.status_interval} minutes")
        return True

    def collect_data(self, inverter):
        # Check all required registers have been returned by the inverter
        if not inverter.validateLatestScrape('timestamp'):
                logging.error(f"PVOutput: Skipped collecting data, Timestamp missing from last scrape")
                return False
        for parameter in self.pvoutput_parameters:
            if not inverter.validateLatestScrape(parameter['register']):
                logging.error(f"PVOutput: Skipped collecting data,  {parameter['register']} missing from last scrape")
                return False

        # Add new data to old data and increase count of data points
        for parameter in self.pvoutput_parameters:
            value = inverter.getRegisterValue(parameter.get('register'))

            if parameter.get('multiple'):
                value = value * parameter.get('multiple')

            # If using Cumulative Energy we just need the last data point, not the average
            if parameter.get('name') == 'v1' and (self.pvoutput_config['cumulative_flag'] == 1 or self.pvoutput_config['cumulative_flag'] == 2):
                self.collected_data[parameter.get('name')] = value
            elif parameter.get('name') == 'v3' and (self.pvoutput_config['cumulative_flag'] == 1 or self.pvoutput_config['cumulative_flag'] == 3):
                self.collected_data[parameter.get('name')] = value
            # Add the last data point to the previous data point if exists, otherwise set as the last data point
            elif self.collected_data.get(parameter.get('name'),False):
                self.collected_data[parameter.get('name')] = round(self.collected_data[parameter.get('name')] + value,3)
            else:
                self.collected_data[parameter.get('name')] = value

        if self.collected_data.get('count',False):
            self.collected_data['count'] +=1
        else:
            self.collected_data['count'] = 1

        logging.debug(f'PVOutput: Data Logged: {self.collected_data}')

        return True

    def publish(self, inverter):
        if self.collect_data(inverter):
            # Process data points every status_interval
            if((time.time() - self.last_publish) >= (self.status_interval * 60)):
                any_data = False
                if inverter.validateLatestScrape('timestamp'):
                    now = datetime.datetime.strptime(inverter.getRegisterValue('timestamp'), "%Y-%m-%d %H:%M:%S")
                    data_point = str(now.strftime("%Y%m%d")) + "," + str(now.strftime("%H:%M"))
                    for x in range(1, 13):
                        field = 'v' + str(x)
                        if self.collected_data.get(field):
                            if x == 1  and (self.pvoutput_config['cumulative_flag'] == 1 or self.pvoutput_config['cumulative_flag'] == 2):
                                value = int(self.collected_data[field])
                            elif x == 3 and (self.pvoutput_config['cumulative_flag'] == 1 or self.pvoutput_config['cumulative_flag'] == 3):
                                value = int(self.collected_data[field])
                            elif x == 6 or x == 7:    # Round to 1 decimal place
                                value = round(self.collected_data[field] / self.collected_data['count'], 1)
                            else:                     # Getting errors when uploading decimals for power/energy so return INT
                                value = int((self.collected_data[field] / self.collected_data['count']))
                            data_point = data_point + "," + str(value)
                            any_data = True
                        else:
                            data_point = data_point + ","
                    self.collected_data = {}

                if any_data:
                    self.batch_data.append(data_point)
                else:
                    logging.warning(f"PVOutput: No data collected in last {(self.status_interval * 60)} minutes")

                # Max upload is 30, if over 30 then remove the oldest one
                if self.batch_data.__len__() > 30:
                    logging.warning(f"PVOutput: Over 30 data points scheduled to upload. max is 30 so removing oldest data point")
                    self.batch_data.pop(0)

                self.batch_count +=1
                if self.batch_count >= self.pvoutput_config['batch_points']:
                    if not self.batch_data.__len__() > 0:
                        logging.warning(f"PVOutput: No data collected in last {((self.status_interval * 60) * self.batch_count)} minutes, Skipping upload")
                        return False
                    elif self.batch_data.__len__() >= 1:
                        payload_data = None
                        for data in self.batch_data:
                            if payload_data:
                                payload_data = payload_data + ";" + data
                            else:
                                payload_data = data

                    payload = {}
                    payload['data'] = payload_data

                    if self.pvoutput_config['cumulative_flag'] > 0:
                        payload['c1'] = self.pvoutput_config['cumulative_flag']

                    try:
                        logging.debug("PVOutput: Request; " + self.url_addbatchstatus + ", " + str(self.headers) + " : " + str(payload))
                        response = requests.post(url=self.url_addbatchstatus, headers=self.headers, params=payload, timeout=3)
                        self.batch_count = 0

                        if response.status_code != requests.codes.ok:
                            logging.error(f"PVOutput: Upload Failed; {str(response.status_code)} Message; {str(response.text)}")
                            logging.error("PVOutput: Request; " + self.url_addbatchstatus + ", " + str(self.headers) + " : " + str(payload))
                        else:
                            self.batch_data = []
                            self.last_publish = time.time()
                            logging.info("PVOutput: Data uploaded")
                    except Exception as err:
                        logging.error(f"PVOutput: Failed to Upload")
                        logging.debug(f"{err}")
                else:
                    logging.info("PVOutput: Data added to next batch upload")
            else:
                logging.info(f"PVOutput: Data logged, next upload in {int(((self.status_interval) * 60) - (time.time() - self.last_publish))} secs")

            self.last_run = time.time()