class export_console(object):
    def __init__(self):
        pass

    # Configure Console
    def configure(self, config, inverter):
        print("+----------------------------------------------+")
        print("{:<46} {:<1}".format("| " + 'Inverter Configuration Settings',"|"))
        print("+----------------------------------------------+")
        print("{:<20} {:<25} {:<1}".format("| " + 'Config',"| " + 'Value', "|"))
        print("+--------------------+-------------------------+")
        for setting, value in inverter.client_config.items():
            print("{:<20} {:<25} {:<1}".format("| " + str(setting), "| " + str(value), "|"))
        for setting, value in inverter.inverter_config.items():
            print("{:<20} {:<25} {:<1}".format("| " + str(setting), "| " + str(value), "|"))
        print("+----------------------------------------------+")

        return True

    def publish(self, inverter):
        print("+----------------------------------------------------------------------+") 
        print("| {:<7} | {:<35} | {:<20} |".format('Address', 'Register','Value'))
        print("+---------+-------------------------------------+----------------------+") 
        for register, value in inverter.latest_scrape.items():
            print("| {:<7} | {:<35} | {:<20} |".format(str(inverter.getRegisterAddress(register)), str(register), str(value) + " " + str(inverter.getRegisterUnit(register))))
        print("+----------------------------------------------------------------------+") 
        print(f"Logged {len(inverter.latest_scrape)} registers to Console")

        return True