from prometheus_client import start_http_server, Gauge, Enum, Info, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR
import logging

# Ignore Python related metrics
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])

class export_prometheus(object):
    def __init__(self):
        self.metrics_config = {}

    def init_metric(self, metric):
        metric_name = metric['metric_name']
        metric_type = metric['type']

        logging.info(f"Prometheus: Initialising metric {metric_name} as type {metric_type}")

        if metric_type == 'Info':
            self.metrics_config[metric_name] =  {
                'metric_type': metric_type,
                'metric': Info(metric_name, metric['description']),
                'publish_info': metric['publish_info']
            }
        elif metric_type == 'Enum':
            self.metrics_config[metric_name] =  {
                'metric_type': metric_type,
                'metric': Enum(metric_name, metric['description'], states=metric['states']),
                'register': metric['register']
            }
        elif metric_type == 'Gauge':
            self.metrics_config[metric_name] =  {
                'metric_type': metric_type,
                'metric': Gauge(metric_name, metric['description'], unit=metric['unit']),
                'register': metric['register'],
                'multiple': metric.get('multiple', 1)
            }
        else:
            logging.warn(f"Unsupported metric type {metric_type}. Ignoring")

    def configure(self, config, inverter):
        try:
            for metric in config['metrics']:
                self.init_metric(metric)

            start_http_server(config.get('port', 8000))
        except Exception as err:
            logging.error(f"Prometheus-Export: Error: {err}")
            return False
        return True

    def publish(self, inverter):
        try:
            latest_scrape = inverter.latest_scrape

            for metric_name, config in self.metrics_config.items():
                if config['metric_type'] == 'Info':
                    publish = {}

                    for info in config['publish_info']:
                        publish[info['key']] = latest_scrape[info['register']]

                    self.metrics_config[metric_name]['metric'].info(publish)
                elif config['metric_type'] == 'Enum':
                    self.metrics_config[metric_name]['metric'].state(latest_scrape[config['register']])
                elif config['metric_type'] == 'Gauge':
                    self.metrics_config[metric_name]['metric'].set(latest_scrape[config['register']] * config['multiple'])

            return True
            logging.debug(f"Prometheus-Published")
        except Exception as err:
            logging.error(f"Prometheus-Publishing: Error: {err}")
            return False
