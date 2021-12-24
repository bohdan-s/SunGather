#!/usr/bin/python3

from SungrowModbusTcpClient import SungrowModbusTcpClient
from SungrowModbusWebClient import SungrowModbusWebClient
from pymodbus.client.sync import ModbusTcpClient
from threading import Thread
from version import __version__
from datetime import datetime

import importlib
import logging
import sys
import getopt
import yaml
import time
import os

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=30,
    datefmt='%Y-%m-%d %H:%M:%S')

try:
    opts, args = getopt.getopt(sys.argv[1:],"hc:v:", "runonce")
except getopt.GetoptError:
    logging.debug(f'No options passed via command line')

configfile = 'config.yaml'

for opt, arg in opts:
    if opt == '-h':
        print(f'\nSunGather {__version__}')
        print(f'usage: python3 sungather.py [options]')
        print(f'\nCommandling arguments override any config file settings')
        print(f'Options and arguments:')
        print(f'-c config.yaml     : Specify config file.')
        print(f'-v 30              : Logging Level, 10 = Debug, 20 = Info, 30 = Warning (default), 40 = Error')
        print(f'--runonce          : Run once then exit')
        print(f'-h                 : print this help message and exit (also --help)')
        print(f'\nExample:')
        print(f'python3 sungather.py -c /full/path/config.yaml\n')
        sys.exit()
    elif opt == '-c':
        configfile = arg     
    elif opt  == '-v':
        if arg.isnumeric():
            if int(arg) >= 0 and int(arg) <= 50:
                loglevel = int(arg)
            else:
                logging.error(f"Valid verbose options: 10 = Debug, 20 = Info, 30 = Warning (default), 40 = Error")
                sys.exit(2)        
        else:
            logging.error(f"Valid verbose options: 10 = Debug, 20 = Info, 30 = Warning (default), 40 = Error")
            sys.exit(2) 
    elif opt == '--runonce':
        runonce = True   

logging.info(f'Starting SunGather {__version__}')

try:
    config = yaml.safe_load(open(configfile))
    logging.info(f"Loaded config: {configfile}")
except Exception as err:
    logging.error(f"Failed: Loading config: {configfile} \n\t\t\t     {err}")
    sys.exit(1)

try:
    registers = yaml.safe_load(open('registers.yaml'))
    logging.info(f"Loaded registers: {os.getcwd()}/registers.yaml")
except Exception as err:
    logging.error(f"Failed: Loading registers: {os.getcwd()}/registers.yaml {err}")
    sys.exit(1)

if not config.get('inverter'):
        logging.error(f"Failed Loading config, missing Inverter settings")
        sys.exit(1)   

if 'loglevel' in locals():
    logging.getLogger().setLevel(loglevel)
else:
    logging.getLogger().setLevel(config['inverter'].get('logging',30))


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

if not config['inverter'].get("connection") == "http":
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
        logging.warning(f'No data returned for {register_type}, {start}:{count}\n\t\t\t\t{str(err)}')
        return

    if rr.isError():
        logging.warning(f"Modbus connection failed: {rr}")
        return

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
                        for supported_model in register.get('models'):
                            if supported_model == inverter.get('device_type_code'):
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
                    register_value = round(register_value * register.get('multiple',0),2)

                # Set the final register name and value after checking model, any adjustments above included 
                if register.get('level',3) <= config['inverter'].get('level',1) or config['inverter'].get('level',1) == 3:
                    if register.get('smart_meter') and config['inverter'].get('smart_meter'):
                        inverter[register_name] = register_value
                    elif register.get('models') and not config['inverter'].get('level',1) == 3:
                        for supported_model in register.get('models'):
                            if supported_model == inverter.get('device_type_code'):
                                inverter[register_name] = register_value
                    else:
                        inverter[register_name] = register_value


    return True

# Inverter Scanning
inverter = {}
model = None

if config['inverter'].get('model'):
    inverter['device_type_code'] = model
    logging.info(f'Bypassing Model Detection, Using config: {model}')
else:
    if load_registers("read", 4999, 1):
        logging.info(f"Detected Model: {inverter.get('device_type_code')}")
    else:
        inverter['device_type_code'] = 'unknown'
        logging.info(f'Model detection failed, please set model in config.py')


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
        if config['inverter'].get('manual_load', False):     # Inverter is returning no data, we need to calculate it manually
            inverter["load_power"] = int(inverter.get('total_active_power')) + int(inverter.get('meter_power'))
    except Exception:
        pass  

    # See if the inverter is running, This is added to inverters so can be read via MQTT etc...
    # It is also used below, as some registers hold the last value on 'stop' so we need to set to 0
    # to help with graphing.
    try:
        if inverter.get('start_stop'):
            if inverter.get('start_stop', False) == 'Start' and inverter.get('work_state_1', False) == 'Run':
                inverter["is_running"] = True
        else:
            if inverter.get('start_stop') == 'Stop':
                inverter["is_running"] = False
    except Exception:
        pass

    if config['inverter'].get('use_local_time',False):
        inverter["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.debug(f'Using Local Computer Time: {inverter.get("timestamp")}')       
        del inverter["year"]
        del inverter["month"]
        del inverter["day"]
        del inverter["hour"]
        del inverter["minute"]
        del inverter["second"]
    else:
        try:
            inverter["timestamp"] = "%s-%s-%s %s:%02d:%02d" % (
                inverter["year"],
                inverter["month"],
                inverter["day"],
                inverter["hour"],
                inverter["minute"],
                inverter["second"],
            )
            logging.debug(f'Using Inverter Time: {inverter.get("timestamp")}')       
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

while True:
    # Scrape the inverter
    success = scrape_inverter()

    for export in exports:
        t = Thread(target=export.publish, args=(inverter,))
        t.start()

#    if args.one_shot:
#        logging.info("Exiting due to --one-shot")
#        break

    if not 'runonce' in locals():
        # Sleep until the next scan
        time.sleep(config['inverter'].get('scan_interval', 30))
    else:
        sys.exit(0)