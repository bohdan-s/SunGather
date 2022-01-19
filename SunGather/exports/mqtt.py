import logging
import json
import paho.mqtt.client as mqtt

class export_mqtt(object):
    def __init__(self):
        self.mqtt_client = None
        self.sensor_topic = None
        self.homeassistant = False
        self.ha_discovery = True
        self.ha_sensors = []
        self.model = None
        self.model_clean = None
        self.inverter_ip = None
        self.mqtt_queue = []

    # Configure MQTT
    def configure(self, config, config_inverter):
        self.mqtt_client = mqtt.Client(client_id="SunGather")
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_publish = self.on_publish

        if config.get('username') and config.get('password'):
            self.mqtt_client.username_pw_set(config.get('username'), config.get('password'))

        if config.get('port') == 8883:
            self.mqtt_client.tls_set()
        
        self.mqtt_client.connect_async(config.get('host'), port=config.get('port', 1883), keepalive=60)
        self.mqtt_client.loop_start()

        self.inverter_ip = config_inverter.get('host')
        self.sensor_topic = config.get('topic', 'inverter/{model}/registers')
        self.homeassistant = config.get('homeassistant', False)

        if self.homeassistant:
            for ha_sensor in config.get('ha_sensors'):
                self.ha_sensors.append(ha_sensor)

        return True

    def on_connect(self, client, userdata, flags, rc):
        logging.info(f"MQTT: Connected {client._host}:{client._port}")

    def on_disconnect(self, client, userdata, rc):
        logging.info(f"MQTT: Server Disconnected code:{rc}")
    
    def on_publish(self, client, userdata, mid):
        self.mqtt_queue.remove(mid)
        logging.info(f"MQTT: Message {mid} Published")

    def publish(self, inverter):
        if not self.mqtt_client.is_connected():
            logging.warning(f'MQTT: Server Disconnected; {self.mqtt_queue.__len__()} messages queued')
        elif self.mqtt_queue.__len__() > 10:
            logging.warning(f'MQTT: {self.mqtt_queue.__len__()} messages queued, this may be due to a MQTT server issue')

        if not self.model:
            self.model = inverter.get('device_type_code', 'unknown')
            self.model_clean = self.model.replace('.','').replace('-','')
            self.sensor_topic = self.sensor_topic.replace('{model}', self.model_clean)

        logging.debug(f'MQTT: Sensor Topic = {self.sensor_topic}')
        logging.debug(f"MQTT: Publishing: {self.sensor_topic} : {json.dumps(inverter)}")
        self.mqtt_queue.append(self.mqtt_client.publish(self.sensor_topic, json.dumps(inverter).replace('"', '\"'), qos=1).mid)

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

                    logging.debug(f'MQTT: Topic; {ha_topic}, Message: {config_msg}')
                    self.mqtt_queue.append(self.mqtt_client.publish(ha_topic, json.dumps(config_msg), retain=True, qos=1).mid)
                self.ha_discovery = False
                logging.info("MQTT: Published Home Assistant Discovery messages")

        return True