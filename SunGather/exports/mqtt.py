import logging
import json
import paho.mqtt.client as mqtt

class export_mqtt(object):
    def __init__(self):
        self._isConfigured = False
        self.mqtt_client = None
        self.sensor_topic = None
        self.homeassistant = False
        self.ha_discovery = True
        self.ha_sensors = []
        self.model = None
        self.model_clean = None
        self.inverter_ip = None

    # Configure MQTT
    def configure(self, config, config_inverter):
        self.mqtt_client = mqtt.Client(client_id="SunGather")

        if config.get('username') and config.get('password'):
            self.mqtt_client.username_pw_set(config.get('username'), config.get('password'))

        if config.get('port') == 8883:
            self.mqtt_client.tls_set()
        
        try:
            self.mqtt_client.connect(config.get('host'), port=config.get('port', 1883))
            self._isConfigured = True
        except Exception as err:
            logging.error(f"MQTT: Connection {config.get('host')}:{config.get('port', 1883)}")
            logging.error(f"MQTT: Error: {err}")
            return False

        self.inverter_ip = config_inverter.get('host')

        self.sensor_topic = config.get('topic', 'inverter/{model}/registers')
        self.homeassistant = config.get('homeassistant', False)

        if self.homeassistant:
            for ha_sensor in config.get('ha_sensors'):
                self.ha_sensors.append(ha_sensor)

        logging.info(f"MQTT: Configured {config.get('host')}:{config.get('port', 1883)}")

        return self._isConfigured

    def publish(self, inverter):
        global mqtt_client

        if not self._isConfigured:
            logging.info("MQTT: Skipped, Initial Configuration Failed")
            return False

        # After a while you'll need to reconnect, so just reconnect before each publish
        self.mqtt_client.reconnect()

        if not self.model:
            self.model = inverter.get('device_type_code', 'unknown')
            self.model_clean = self.model.replace('.','').replace('-','')
            self.sensor_topic = self.sensor_topic.replace('{model}', self.model_clean)

            logging.debug(f'MQTT: Sensor Topic = {self.sensor_topic}')

        logging.debug(f"MQTT: Publishing: {self.sensor_topic} : {json.dumps(inverter)}")
        result = self.mqtt_client.publish(self.sensor_topic, json.dumps(inverter).replace('"', '\"'))
        result.wait_for_publish()

        if self.homeassistant:
            if self.ha_discovery:
                for ha_sensor in self.ha_sensors:
                    config_msg = {}
                    if ha_sensor.get('name'):
                        ha_topic = 'homeassistant/' + ha_sensor.get('sensor_type', 'sensor') + '/inverter/' + ha_sensor.get('name').lower().replace(' ','_') + '/config'
                        config_msg['name'] = "Inverter " + ha_sensor.get('name')
                        config_msg['unique_id'] = "inverter_" + ha_sensor.get('name').lower().replace(' ','_')
                    config_msg['state_topic'] = self.sensor_topic
                    config_msg['value_template'] = "{{ value_json." + ha_sensor.get('register') + " }}"
                    if ha_sensor.get('unit'):
                        config_msg['unit_of_measurement'] = ha_sensor.get('unit')
                    if ha_sensor.get('dev_class'):
                        config_msg['device_class'] = ha_sensor.get('dev_class')
                    if ha_sensor.get('state_class'):
                        config_msg['state_class'] = ha_sensor.get('state_class')
                    if ha_sensor.get('payload_on'):
                        config_msg['payload_on'] = ha_sensor.get('payload_on')
                    if ha_sensor.get('payload_off'):
                        config_msg['payload_off'] = ha_sensor.get('payload_off')
                    config_msg['ic'] = "mdi:solar-power"
                    config_msg['device'] = { "name":"Solar Inverter", "mf":"Sungrow", "mdl":self.model, "connections":[["address", self.inverter_ip ]]}

                    result = self.mqtt_client.publish(ha_topic, json.dumps(config_msg), retain=True)
                    result.wait_for_publish()
                logging.info("MQTT: Published Home Assistant Discovery messages")
                self.ha_discovery = False

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            # See https://github.com/eclipse/paho.mqtt.python/blob/master/src/paho/mqtt/client.py#L149 for error code mapping
            logging.error(f"MQTT: Failed to publish with error code: {result.rc}")
        else:
            logging.info("MQTT: Published")

        return result