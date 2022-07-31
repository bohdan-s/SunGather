from prometheus_client import start_http_server, Gauge, Enum, Info, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR
import logging

# Ignore Python related metrics
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])

class export_prometheus(object):
    def configure(self, config, inverter):
        try:
            self.device_type_code = Info('inverter_device_type_code', 'Device Type Code')
            self.run_state = Enum("inverter_run_state", "Run State", states=["ON", "OFF"])
            self.daily_power_yields = Gauge("inverter_daily_power_yield_watt_hours_total", "Daily Power Yields")
            self.total_power_yields = Gauge("inverter_total_power_yield_watt_hours_total", "Total Power Yields")
            self.internal_temperature = Gauge("inverter_internal_temperature_celsius", "Internal Temperature")
            self.phase_a_voltage = Gauge("inverter_phase_a_voltage_volts", "Phase A Voltage")
            self.total_active_power = Gauge("inverter_active_power_watts_total", "Total Active Power")
            self.work_state = Info('inverter_work_state', 'Work State')
            self.meter_power = Gauge("inverter_meter_power_watts_total", "Meter Power")

            start_http_server(config.get('port', 8000))
        except Exception as err:
            logging.error(f"Prometheus-Export: Error: {err}")
            return False
        return True


    def publish(self, inverter):
        try:
            latest_scrape = inverter.latest_scrape

            self.device_type_code.info({'device_type_code': latest_scrape['device_type_code']})
            self.run_state.state(latest_scrape['run_state'])
            self.daily_power_yields.set(latest_scrape['daily_power_yields'] * 1000)
            self.total_power_yields.set(latest_scrape['total_power_yields'] * 1000)
            self.internal_temperature.set(latest_scrape['internal_temperature'])
            self.phase_a_voltage.set(latest_scrape['phase_a_voltage'])
            self.total_active_power.set(latest_scrape['total_active_power'])
            self.work_state.info({'work_state': latest_scrape['work_state_1']})
            self.meter_power.set(latest_scrape['meter_power'])

            logging.debug(f"Prometheus-Published")
        except Exception as err:
            logging.error(f"Prometheus-Publishing: Error: {err}")
            return False
        return True
