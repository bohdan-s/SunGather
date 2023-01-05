#!/usr/bin/python3

from SungrowClient import SungrowClient
from version import __version__

import importlib
import logging
import logging.handlers
import sys
import getopt
import yaml
import time

def main():
    configfilename = 'config.yaml'
    registersfilename = 'registers-sungrow.yaml'
    logfolder = ''

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hc:r:l:v:", "runonce")
    except getopt.GetoptError:
        logging.debug(f'No options passed via command line')

    for opt, arg in opts:
        if opt == '-h':
            print(f'\nSunGather {__version__}')
            print(f'\nhttps://sungather.app')
            print(f'usage: python3 sungather.py [options]')
            print(f'\nCommandling arguments override any config file settings')
            print(f'Options and arguments:')
            print(f'-c config.yaml             : Specify config file.')
            print(f'-r registers-file.yaml     : Specify registers file.')
            print(f'-l /logs/                  : Specify folder to store logs.')
            print(f'-v 30                      : Logging Level, 10 = Debug, 20 = Info, 30 = Warning (default), 40 = Error')
            print(f'--runonce                  : Run once then exit')
            print(f'-h                         : print this help message and exit (also --help)')
            print(f'\nExample:')
            print(f'python3 sungather.py -c /full/path/config.yaml\n')
            sys.exit()
        elif opt == '-c':
            configfilename = arg
        elif opt == '-r':
            registersfilename = arg
        elif opt == '-l':
            logfolder = arg    
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
    logging.info(f'Need Help? https://github.com/bohdan-s/SunGather')
    logging.info(f'NEW HomeAssistant Add-on: https://github.com/bohdan-s/hassio-repository')

    try:
        configfile = yaml.safe_load(open(configfilename, encoding="utf-8"))
        logging.info(f"Loaded config: {configfilename}")
    except Exception as err:
        logging.error(f"Failed: Loading config: {configfilename} \n\t\t\t     {err}")
        sys.exit(1)
    if not configfile.get('inverter'):
        logging.error(f"Failed Loading config, missing Inverter settings")
        sys.exit(f"Failed Loading config, missing Inverter settings")   

    try:
        registersfile = yaml.safe_load(open(registersfilename, encoding="utf-8"))
        logging.info(f"Loaded registers: {registersfilename}")
        logging.info(f"Registers file version: {registersfile.get('version','UNKNOWN')}")
    except Exception as err:
        logging.error(f"Failed: Loading registers: {registersfilename}  {err}")
        sys.exit(f"Failed: Loading registers: {registersfilename} {err}")
   
    config_inverter = {
        "host": configfile['inverter'].get('host',None),
        "port": configfile['inverter'].get('port',502),
        "timeout": configfile['inverter'].get('timeout',10),
        "retries": configfile['inverter'].get('retries',3),
        "slave": configfile['inverter'].get('slave',0x01),
        "scan_interval": configfile['inverter'].get('scan_interval',30),
        "connection": configfile['inverter'].get('connection',"modbus"),
        "model": configfile['inverter'].get('model',None),
        "smart_meter": configfile['inverter'].get('smart_meter',False),
        "use_local_time": configfile['inverter'].get('use_local_time',False),
        "log_console": configfile['inverter'].get('log_console','WARNING'),
        "log_file": configfile['inverter'].get('log_file','OFF'),
        "level": configfile['inverter'].get('level',1)
    }

    if 'loglevel' in locals():
        logger.handlers[0].setLevel(loglevel)
    else:
        logger.handlers[0].setLevel(config_inverter['log_console'])

    if not config_inverter['log_file'] == "OFF":
        if config_inverter['log_file'] == "DEBUG" or config_inverter['log_file'] == "INFO" or config_inverter['log_file'] == "WARNING" or config_inverter['log_file'] == "ERROR":
            logfile = logfolder + "SunGather.log"
            fh = logging.handlers.RotatingFileHandler(logfile, mode='w', encoding='utf-8', maxBytes=10485760, backupCount=10) # Log 10mb files, 10 x files = 100mb
            fh.formatter = logger.handlers[0].formatter
            fh.setLevel(config_inverter['log_file'])
            logger.addHandler(fh)
        else:
            logging.warning(f"log_file: Valid options are: DEBUG, INFO, WARNING, ERROR and OFF")

    logging.info(f"Logging to console set to: {logging.getLevelName(logger.handlers[0].level)}")
    if logger.handlers.__len__() == 3:
        logging.info(f"Logging to file set to: {logging.getLevelName(logger.handlers[2].level)}")
    
    logging.debug(f'Inverter Config Loaded: {config_inverter}')    

    if config_inverter.get('host'):
        inverter = SungrowClient.SungrowClient(config_inverter)
    else:
        logging.error(f"Error: host option in config is required")
        sys.exit("Error: host option in config is required")

    if not inverter.checkConnection():
        logging.error(f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}")
        sys.exit(f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}")       

    inverter.configure_registers(registersfile)
    if not inverter.inverter_config['connection'] == "http": inverter.close()
    
    # Now we know the inverter is working, lets load the exports
    exports = []
    if configfile.get('exports'):
        for export in configfile.get('exports'):
            try:
                if export.get('enabled', False):
                    export_load = importlib.import_module("exports." + export.get('name'))
                    logging.info(f"Loading Export: exports\{export.get('name')}")
                    exports.append(getattr(export_load, "export_" + export.get('name'))())
                    retval = exports[-1].configure(export, inverter)
            except Exception as err:
                logging.error(f"Failed loading export: {err}" +
                            f"\n\t\t\t     Please make sure {export.get('name')}.py exists in the exports folder")

    scan_interval = config_inverter.get('scan_interval')

    # Core polling loop
    while True:
        loop_start = time.perf_counter()

        inverter.checkConnection()

        # Scrape the inverter
        success = inverter.scrape()

        if(success):
            for export in exports:
                export.publish(inverter)
            if not inverter.inverter_config['connection'] == "http": inverter.close()
        else:
            inverter.disconnect()
            logging.warning(f"Data collection failed, skipped exporting data. Retying in {scan_interval} secs")

        loop_end = time.perf_counter()
        process_time = round(loop_end - loop_start, 2)
        logging.debug(f'Processing Time: {process_time} secs')

        if 'runonce' in locals():
            sys.exit(0)
        
        # Sleep until the next scan
        if scan_interval - process_time <= 1:
            logging.warning(f"SunGather is taking {process_time} to process, which is longer than interval {scan_interval}, Please increase scan interval")
            time.sleep(process_time)
        else:
            logging.info(f'Next scrape in {int(scan_interval - process_time)} secs')
            time.sleep(scan_interval - process_time)    

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger('')
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)

if __name__== "__main__":
    main()

sys.exit()
