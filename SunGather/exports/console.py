import logging

class export_console(object):
    def __init__(self):
        return

    # Configure MQTT
    def configure(self, config, config_inverter):
        logging.info("Configured Console Logging")

    def publish(self, inverter):

        print("{:<40} {:<25}".format('Register','Value'))
        for register in inverter:
            print("{:<40} {:<25}".format(register,str(inverter.get(register))))

        print(f"Logged {len(inverter)} registers to Console")

        return