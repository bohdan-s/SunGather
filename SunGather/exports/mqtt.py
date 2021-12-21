import logging
import json
import paho.mqtt.client as mqtt

class export_mqtt(object):
    def __init__(self):
        self.mqtt_client = None
        self.sensor_topic = None
        self.ha_discovery = False
        self.ha_topics = []
        self.update_model = True

    # Configure MQTT
    def configure(self, config):
        self.mqtt_client = mqtt.Client("pv_data")

        if config.get('username') and config.get('password'):
            self.mqtt_client.username_pw_set(config.get('username'), config.get('password'))

        if config.get('port') == 8883:
            self.mqtt_client.tls_set()
        
        self.mqtt_client.connect(config.get('host'), port=config.get('port', 1883))

        self.sensor_topic = config.get('topic', 'tele/inverter_{model}/SENSOR')
        self.ha_discovery = config.get('ha_discovery', False)

        if self.ha_discovery:
            for ha_topic in config.get('ha_topics'):
                self.ha_topics.append(ha_topic)

        logging.info("Configured MQTT Client")

    def publish(self, inverter):
        global mqtt_client

        if (self.update_model):
            self.sensor_topic = self.sensor_topic.replace('{model}', inverter.get('device_type_code', 'unknown').replace('.',''))
            self.update_model = False

        if self.ha_discovery:
            self.mqtt_client.reconnect()
            logging.info("Publishing Home Assistant Discovery messages")
            discovery_topic = 'homeassistant/sensor/inverter/{}/config'
            discovery_payload = '{{"name":"Inverter {}", "uniq_id":"{}", "stat_t":"{}", "json_attr_t":"{}", "unit_of_meas":"{}", "dev_cla":"{}", "state_class":"{}", "val_tpl":"{{{{ value_json.{} }}}}", "ic":"mdi:solar-power", "device":{{ "name":"Solar Inverter", "mf":"Sungrow", "mdl":"{}", "connections":[["address", "' + self.mqtt_client._host + '" ]]}}}}'   

            for ha_topic in self.ha_topics:
                msg = discovery_payload.format( ha_topic.get('name'),  "inverter_" + ha_topic.get('name').lower().replace(' ','_'),    self.sensor_topic,   self.sensor_topic,  ha_topic.get('unit'),   ha_topic.get('dev_class'),  ha_topic.get('state_class'),    ha_topic.get('register'), inverter.get('device_type_code', 'unknown').replace('.',''))
                result = self.mqtt_client.publish(discovery_topic.format(ha_topic.get('name').lower().replace(' ','_')), msg, retain=True)
                result.wait_for_publish()
            self.ha_discovery = False

        # After a while you'll need to reconnect, so just reconnect before each publish
        self.mqtt_client.reconnect()
        result = self.mqtt_client.publish(self.sensor_topic, json.dumps(inverter).replace('"', '\"'))
        result.wait_for_publish()

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            # See https://github.com/eclipse/paho.mqtt.python/blob/master/src/paho/mqtt/client.py#L149 for error code mapping
            logging.error(f"Failed to publish to MQTT with error code: {result.rc}")
        else:
            logging.info("Published to MQTT")

        return result