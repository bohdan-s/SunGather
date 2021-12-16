#!/usr/bin/python3

from SungrowModbusTcpClient import SungrowModbusTcpClient
from SungrowModbusWebClient import SungrowModbusWebClient
from pymodbus.client.sync import ModbusTcpClient
from threading import Thread
from version import __version__

import importlib
import logging
import sys
import yaml
import time

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=20,
    datefmt='%Y-%m-%d %H:%M:%S')
logging.info(f'Starting SunGather {__version__}')

#opts = sys.getopt(sys.argv[1:],"hi:o:",["ifile=","ofile="])

try:
    config = yaml.safe_load(open('config.yaml'))
    logging.info(f"Loaded config: config.yaml")
except Exception as err:
    logging.error(f"Failed: Loading config: config.yaml {err}")
    sys.exit(1)

logging.getLogger().setLevel(config['inverter'].get('logging',30))

try:
    registers = yaml.safe_load(open('registers.yaml'))
    logging.info(f"Loaded registers: registers.yaml")
except Exception as err:
    logging.error(f"Failed: Loading registers: registers.yaml {err}")
    sys.exit(1)

exports = []
if config.get('exports'):
    for export in config.get('exports'):
        try:
            if export.get('enabled', True):
                export_load = importlib.import_module("exports." + export.get('name'))
                logging.info(f"Loaded Export: exports\{export.get('name')}")
                exports.append(getattr(export_load, "export_" + export.get('name'))())
                exports[-1].configure(export)
                logging.info(f"Configured export: {export.get('name')}")
        except Exception as err:
            logging.error(f"Failed loading export: {err}" +
                           f"\n\t\t\t     Please make sure {export.get('name')}.py exists in the exports folder")



client_payload = {
    "host": config['inverter'].get('host', '127.0.0.1'),
    "port": config['inverter'].get('port', 502),
    "timeout": config['inverter'].get('timeout', 10),
    "retries": config['inverter'].get('retries', 3),
    "RetryOnEmpty": config['inverter'].get('RetryOnEmpty', False),
}

if config['inverter'].get("connection") == "http":
    client_payload['port'] = config['inverter'].get('port', '8082')
    client = SungrowModbusWebClient.SungrowModbusWebClient(**client_payload)
elif config['inverter'].get("connection") == "sungrow":
    client = SungrowModbusTcpClient.SungrowModbusTcpClient(**client_payload)
elif config['inverter'].get("connection") == "modbus":
    client = ModbusTcpClient(**client_payload)
else:
    logging.warning(f'inverter > connection not specified, defaulting to ModbusTcpClient')
    client = ModbusTcpClient(**client_payload)
logging.info("Connection: " + str(client))

client.connect()
client.close()

def load_registers(register_type, start, count=100):
    try:
        logging.debug(f'load_registers: {register_type}, {start}:{count}')
        if register_type == "read":
            rr = client.read_input_registers(start,count=count, unit=config['inverter'].get('slave', 0x01))
        elif register_type == "hold":
            rr = client.read_holding_registers(start,count=count, unit=config['inverter'].get('slave', 0x01))
        else:
            raise RuntimeError(f"Unsupported register type: {type}")
    except Exception as err:
        logging.warning(f'No data. Try increasing the timeout or scan interval for {register_type}, {start}:{count}: {err}')
        return True

    if rr.isError():
        logging.warning("Modbus connection failed")
        return False

    if not hasattr(rr, 'registers'):
        logging.warning("No registers returned")
        return

    if len(rr.registers) != count:
        logging.warning(f"Mismatched number of registers read {len(rr.registers)} != {count}")
        return

    for num in range(0, count):
        run = int(start) + num + 1

        for register in registers['registers'][0]['read']:
            if register_type == "read" and register['address'] == run:
                register_name = register['name']

                # We convert a system response to a human value 
                register_value = None
                if register.get('datarange'):
                    for value in register.get('datarange'):
                        if value['response'] == rr.registers[num]:
                            register_value = value['value']
                if not register_value:
                    register_value = rr.registers[num]

                # Adjust the value if needed
                if register.get('indicator'):
                    indicator_value = rr.registers[num+1]
                    if indicator_value == 65535:
                        register_value = -1 * (65535 - register_value)

                # If xFF (U 65535 / S 32767) then change to 0, looks better when logging / graphing
                if register.get('datatype') == 'S16' and register_value == 32767:
                    register_value = 0
                elif (register.get('datatype') == 'U16' or register.get('datatype') == 'S32') and register_value == 65535:
                    register_value = 0

                if register.get('multiple'):
                    register_value = round(register_value * register.get('multiple'),2)

                # Set the final register name and value after checking model, any adjustments above included 
                if register.get('level',3) <= config['inverter'].get('level',1) or config['inverter'].get('level',1) == 3:
                    if register.get('smart_meter') and config['inverter'].get('smart_meter'):
                        inverter[register_name] = register_value
                    elif register.get('models') and not config['inverter'].get('level',1) == 3:
                        for model in register.get('models'):
                            if model == config['inverter'].get('model'):
                                inverter[register_name] = register_value
                    else:
                        inverter[register_name] = register_value

        for register in registers['registers'][1]['hold']:
            if register_type == "hold" and register['address'] == run:
                register_name = register['name']
                # We convert a system response to a human value 
                register_value = None
                if register.get('datarange'):
                    for value in register.get('datarange'):
                        if value['response'] == rr.registers[num]:
                            register_value = value['value']
                if not register_value:
                    register_value = rr.registers[num]

                # Adjust the value if needed
                if register.get('indicator'):
                    indicator_value = rr.registers[num+1]
                    if indicator_value == 65535:
                        register_value = -1 * (65535 - register_value)

                # If xFF (U 65535 / S 32767) then change to 0, looks better when logging / graphing
                if register.get('datatype') == 'S16' and register_value == 32767:
                    register_value = 0
                elif (register.get('datatype') == 'U16' or register.get('datatype') == 'S32') and register_value == 65535:
                    register_value = 0

                if register.get('multiple'):
                    register_value = round(register_value * register.get('multiple'),2)

                # Set the final register name and value after checking model, any adjustments above included
                if register.get('level',3) <= config['inverter'].get('level',1) or config['inverter'].get('level',1) == 3:
                    if register.get('smart_meter') and config['inverter'].get('smart_meter'):
                        inverter[register_name] = register_value
                    elif register.get('models') and not config['inverter'].get('level',1) == 3:
                        for model in register.get('models'):
                            if model == config['inverter'].get('model'):
                                inverter[register_name] = register_value
                    else:
                        inverter[register_name] = register_value

    return True

# Inverter Scanning
inverter = {}
model = None

# Core monitoring loop
def scrape_inverter():
    """ Connect to the inverter and scrape the metrics """
    client.connect()

    for scan in registers['scan']:
        if scan.get('read'):
            for subscan in registers['scan'][0]['read']:
                if subscan.get('level',3) <= config['inverter'].get('level',1) or config['inverter'].get('level',1) == 3:
                    if not subscan.get('hybrid', False):
                        logging.debug(f'Scanning: read, {subscan.get("start")}:{subscan.get("range")}')
                        if not load_registers("read", int(subscan.get('start')), int(subscan.get('range'))):
                            return False
                    elif subscan.get('hybrid', False) and config['inverter'].get('hybrid',False):
                        logging.debug(f'Scanning: read, {subscan.get("start")}:{subscan.get("range")}')
                        if not load_registers("read", int(subscan.get('start')), int(subscan.get('range'))):
                            return False
        if scan.get('hold'):
            for subscan in registers['scan'][1]['hold']:
                    if not subscan.get('hybrid', False):
                        logging.debug(f'Scanning: hold, {subscan.get("start")}:{subscan.get("range")}')
                        if not load_registers("hold", int(subscan.get('start')), int(subscan.get('range'))):
                            return False
                    elif subscan.get('hybrid', False) and config['inverter'].get('hybrid',False):
                        logging.debug(f'Scanning: hold, {subscan.get("start")}:{subscan.get("range")}')
                        if not load_registers("hold", int(subscan.get('start')), int(subscan.get('range'))):
                            return False

    # Create a registers for Power imported and exported to/from Grid
    if config['inverter'].get('level',1) >= 1:
        try:
            inverter["export_to_grid"] = 0
            inverter["import_from_grid"] = 0
            power = inverter.get('meter_power', inverter.get('export_power', 0))
            if power < 0:
                inverter["export_to_grid"] = abs(power)
            elif power >= 0:
                inverter["import_from_grid"] = power
        except Exception:
            pass

    try:
        inverter["timestamp"] = "%s-%s-%s %s:%02d:%02d" % (
            inverter["year"],
            inverter["month"],
            inverter["day"],
            inverter["hour"],
            inverter["minute"],
            inverter["second"],
        )
        del inverter["year"]
        del inverter["month"]
        del inverter["day"]
        del inverter["hour"]
        del inverter["minute"]
        del inverter["second"]
    except Exception:
        pass

    client.close()
    return True

if load_registers("read", 4999, 1):
    model = inverter.get('device_type_code')
    logging.info(f'Detected Model: {model}')
if not config['inverter'].get('model'):
    config['inverter']['model'] = model
elif not model == config['inverter'].get('model'):
    logging.warn(f'Model specified in config {config["inverter"].get("model")} does not match model reported by inverter {model}')

while True:
    # Scrape the inverter
    success = scrape_inverter()

    for export in exports:
        t = Thread(target=export.publish, args=(inverter,))
        t.start()

#    if args.one_shot:
#        logging.info("Exiting due to --one-shot")
#        break

    # Sleep until the next scan
    time.sleep(config['inverter'].get('scan_interval', 30))