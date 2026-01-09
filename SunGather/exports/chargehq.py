import logging
import requests
import time

class export_chargehq(object):
    """
    ChargeHQ Push API export
    See: https://chargehq.net/kb/push-api

    Pushes solar/battery data to ChargeHQ for EV charging optimization.
    Rate limit: minimum 30 seconds between calls (60 seconds recommended).
    """

    def __init__(self):
        self.api_url = "https://api.chargehq.net/api/public/push-solar-data"
        self.last_push = 0

    def configure(self, config, inverter):
        self.api_key = config.get('api_key')
        if not self.api_key:
            logging.error("ChargeHQ: api_key is required")
            return False

        # Push interval in seconds (minimum 30, default 60)
        self.push_interval = max(30, config.get('push_interval', 60))

        # Register mappings - users can override these in config
        # Defaults work for most Sungrow hybrid inverters
        self.reg_production = config.get('register_production', 'total_active_power')
        self.reg_consumption = config.get('register_consumption', 'load_power_hybrid')
        self.reg_net_import = config.get('register_net_import', 'export_power_hybrid')
        self.reg_battery_power = config.get('register_battery_power', 'battery_power')
        self.reg_battery_soc = config.get('register_battery_soc', 'battery_level')

        # Whether net_import register is inverted (export_power_hybrid is positive when exporting)
        self.invert_net_import = config.get('invert_net_import', True)

        logging.info(f"ChargeHQ: Configured with push interval {self.push_interval}s")
        return True

    def publish(self, inverter):
        # Rate limiting
        now = time.time()
        if (now - self.last_push) < self.push_interval:
            remaining = int(self.push_interval - (now - self.last_push))
            logging.debug(f"ChargeHQ: Waiting {remaining}s before next push")
            return True

        payload = {
            "apiKey": self.api_key,
            "siteMeters": {}
        }

        site_meters = payload["siteMeters"]

        # Production (solar generation) - convert W to kW
        production = self._get_register_value(inverter, self.reg_production)
        if production is not None:
            site_meters["production_kw"] = round(production / 1000, 3)

        # Consumption (load power) - convert W to kW
        consumption = self._get_register_value(inverter, self.reg_consumption)
        if consumption is not None:
            site_meters["consumption_kw"] = round(abs(consumption) / 1000, 3)

        # Net import (positive = importing, negative = exporting) - convert W to kW
        net_import = self._get_register_value(inverter, self.reg_net_import)
        if net_import is not None:
            if self.invert_net_import:
                net_import = -net_import  # export_power_hybrid is positive when exporting
            site_meters["net_import_kw"] = round(net_import / 1000, 3)

        # Battery discharge (positive = discharging, negative = charging) - convert W to kW
        battery_power = self._get_register_value(inverter, self.reg_battery_power)
        if battery_power is not None:
            site_meters["battery_discharge_kw"] = round(battery_power / 1000, 3)

        # Battery SOC (ChargeHQ expects 0-1, battery_level is 0-100%)
        battery_soc = self._get_register_value(inverter, self.reg_battery_soc)
        if battery_soc is not None:
            site_meters["battery_soc"] = round(battery_soc / 100, 3)

        # Only push if we have at least production data
        if "production_kw" not in site_meters:
            logging.warning("ChargeHQ: No production data available, skipping push")
            return False

        try:
            logging.debug(f"ChargeHQ: Pushing data: {site_meters}")
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 200:
                self.last_push = now
                logging.info(f"ChargeHQ: Data pushed successfully - production={site_meters.get('production_kw', 0)}kW")
                return True
            else:
                logging.error(f"ChargeHQ: Push failed with status {response.status_code}: {response.text}")
                return False

        except requests.exceptions.Timeout:
            logging.error("ChargeHQ: Request timed out")
            return False
        except requests.exceptions.RequestException as err:
            logging.error(f"ChargeHQ: Request failed: {err}")
            return False

    def _get_register_value(self, inverter, register_name):
        """Get a register value if it exists in the latest scrape."""
        if not register_name:
            return None
        if not inverter.validateLatestScrape(register_name):
            logging.debug(f"ChargeHQ: Register {register_name} not in latest scrape")
            return None
        value = inverter.getRegisterValue(register_name)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logging.warning(f"ChargeHQ: Could not convert {register_name}={value} to float")
            return None
