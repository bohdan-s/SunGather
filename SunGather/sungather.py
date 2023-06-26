#!/usr/bin/python3

from SungrowClient import SungrowClient
from version import __version__

import configargparse
import importlib
import logging
import logging.handlers
import sys
import getopt
import yaml
import time


def arguments():
    """
    command line arguments
    """
    parser = configargparse.ArgumentParser(
        prog="sungather",
        auto_env_var_prefix="SUNGATHER_",
        add_env_var_help=True,
    )
    parser.add("--version", action="version", version=__version__)
    parser.add("--config", "-c", default="config.yaml", help="Specify config file.")
    parser.add(
        "--registers",
        "-r",
        default="registers-sungrow.yaml",
        help="Specify registers file.",
    )
    parser.add("--logs", "-l", help="Specify folder to store logs.")
    parser.add(
        "--verbosity",
        "-v",
        type=int,
        default=30,
        choices=[10, 20, 30, 40],
        help="Logging Level, 10 = Debug, 20 = Info, 30 = Warning, 40 = Error",
    )
    parser.add("--runonce", action="store_true", help="Run once then exit.")
    return parser.parse_known_args()


def main():
    """
    sungather command line tool
    """
    args, extra_args = arguments()
    logging.info(f"Starting SunGather {__version__}")
    logging.info("Need Help? https://github.com/bohdan-s/SunGather")
    logging.info(
        "NEW HomeAssistant Add-on: https://github.com/bohdan-s/hassio-repository"
    )

    try:
        configfile = yaml.safe_load(open(args.config, encoding="utf-8"))
        logging.info(f"Loaded config: {args.config}")
    except Exception as err:
        logging.error(f"Failed: Loading config: {args.config} \n\t\t\t     {err}")
        sys.exit(1)
    if not configfile.get("inverter"):
        logging.error("Failed Loading config, missing Inverter settings")
        sys.exit("Failed Loading config, missing Inverter settings")

    try:
        registersfile = yaml.safe_load(open(args.registers, encoding="utf-8"))
        logging.info(f"Loaded registers: {args.registers}")
        logging.info(
            f"Registers file version: {registersfile.get('version','UNKNOWN')}"
        )
    except Exception as err:
        logging.error(f"Failed: Loading registers: {args.registers}  {err}")
        sys.exit(f"Failed: Loading registers: {args.registers} {err}")

    config_inverter = {
        "host": configfile["inverter"].get("host", None),
        "port": configfile["inverter"].get("port", 502),
        "timeout": configfile["inverter"].get("timeout", 10),
        "retries": configfile["inverter"].get("retries", 3),
        "slave": configfile["inverter"].get("slave", 0x01),
        "scan_interval": configfile["inverter"].get("scan_interval", 30),
        "connection": configfile["inverter"].get("connection", "modbus"),
        "model": configfile["inverter"].get("model", None),
        "smart_meter": configfile["inverter"].get("smart_meter", False),
        "use_local_time": configfile["inverter"].get("use_local_time", False),
        "log_console": configfile["inverter"].get("log_console", "WARNING"),
        "log_file": configfile["inverter"].get("log_file", "OFF"),
        "level": configfile["inverter"].get("level", 1),
    }

    logger.handlers[0].setLevel(args.verbosity)

    if not config_inverter["log_file"] == "OFF":
        if (
            config_inverter["log_file"] == "DEBUG"
            or config_inverter["log_file"] == "INFO"
            or config_inverter["log_file"] == "WARNING"
            or config_inverter["log_file"] == "ERROR"
        ):
            logfile = args.logs + "SunGather.log"
            fh = logging.handlers.RotatingFileHandler(
                logfile, mode="w", encoding="utf-8", maxBytes=10485760, backupCount=10
            )  # Log 10mb files, 10 x files = 100mb
            fh.formatter = logger.handlers[0].formatter
            fh.setLevel(config_inverter["log_file"])
            logger.addHandler(fh)
        else:
            logging.warning(
                "log_file: Valid options are: DEBUG, INFO, WARNING, ERROR and OFF"
            )

    logging.info(
        f"Logging to console set to: {logging.getLevelName(logger.handlers[0].level)}"
    )
    if logger.handlers.__len__() == 3:
        logging.info(
            f"Logging to file set to: {logging.getLevelName(logger.handlers[2].level)}"
        )

    logging.debug(f"Inverter Config Loaded: {config_inverter}")

    if config_inverter.get("host"):
        inverter = SungrowClient.SungrowClient(config_inverter)
    else:
        logging.error("Error: host option in config is required")
        sys.exit("Error: host option in config is required")

    if not inverter.checkConnection():
        logging.error(
            f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}"
        )
        sys.exit(
            f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}"
        )

    inverter.configure_registers(registersfile)
    if not inverter.inverter_config["connection"] == "http":
        inverter.close()

    # Now we know the inverter is working, lets load the exports
    exports = []
    if configfile.get("exports"):
        for export in configfile.get("exports"):
            try:
                if export.get("enabled", False):
                    export_load = importlib.import_module(
                        "SunGather.exports." + export.get("name")
                    )
                    logging.info(f"Loading Export: exports\{export.get('name')}")
                    exports.append(
                        getattr(export_load, "export_" + export.get("name"))()
                    )
                    retval = exports[-1].configure(export, inverter)
            except Exception as err:
                logging.error(
                    f"Failed loading export: {err}"
                    + f"\n\t\t\t     Please make sure {export.get('name')}.py exists in the exports folder"
                )

    scan_interval = config_inverter.get("scan_interval")

    # Core polling loop
    while True:
        loop_start = time.perf_counter()

        inverter.checkConnection()

        # Scrape the inverter
        success = inverter.scrape()

        if success:
            for export in exports:
                export.publish(inverter)
            if not inverter.inverter_config["connection"] == "http":
                inverter.close()
        else:
            inverter.disconnect()
            logging.warning(
                f"Data collection failed, skipped exporting data. Retying in {scan_interval} secs"
            )

        loop_end = time.perf_counter()
        process_time = round(loop_end - loop_start, 2)
        logging.debug(f"Processing Time: {process_time} secs")

        if "runonce" in locals():
            sys.exit(0)

        # Sleep until the next scan
        if scan_interval - process_time <= 1:
            logging.warning(
                f"SunGather is taking {process_time} to process, which is longer than interval {scan_interval}, Please increase scan interval"
            )
            time.sleep(process_time)
        else:
            logging.info(f"Next scrape in {int(scan_interval - process_time)} secs")
            time.sleep(scan_interval - process_time)


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("")
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)

if __name__ == "__main__":
    main()

sys.exit()
