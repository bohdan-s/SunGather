import logging

class export_console(object):
    def __init__(self):
        return

    # Configure Console
    def configure(self, config, config_inverter):
        logging.info("Console: Configured")
        print("{:<20} {:<25}".format('Config','Value'))
        for setting in config_inverter:
            print("{:<40} {:<25}".format(setting,str(config_inverter.get(setting))))

    def publish(self, inverter):

        print("{:<40} {:<25}".format('Register','Value'))
        for register in inverter:
            print("{:<40} {:<25}".format(register,str(inverter.get(register))))

        print(f"Logged {len(inverter)} registers to Console")

        return