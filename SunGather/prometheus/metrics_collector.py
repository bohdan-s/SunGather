from prometheus_client import generate_latest, Gauge, Enum, Info, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR
import logging

# Ignore Python related metrics
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])


class PrometheusMetricsCollector(object):
    def __init__(self):
        self.metrics_config = {}

    def configure(self, config):
        try:
            for metric_config in config['metrics']:
                self.setup_metric_collectors(metric_config)
        except Exception as err:
            logging.error(f"Prometheus-Export: Error: {err}")
            return False
        return True

    def setup_metric_collectors(self, metric_config):
        metric_name = metric_config['metric_name']
        metric_type = metric_config['type']

        logging.debug(f"Prometheus: Initialising metric {metric_name} as type {metric_type}")

        if metric_type == 'Info':
            self.setup_info_collector(metric_config)
        elif metric_type == 'Enum':
            self.setup_enum_collector(metric_config)
        elif metric_type == 'Gauge':
            self.setup_gauge_collector(metric_config)
        else:
            logging.warning(f"Unsupported metric type {metric_type}. Ignoring")

    def setup_gauge_collector(self, metric_config):
        metric_name = metric_config['metric_name']
        metric_type = metric_config['type']

        self.metrics_config[metric_name] = {
            'metric_type': metric_type,
            'metric': Gauge(metric_name, metric_config['description'], unit=metric_config['unit']),
            'register': metric_config['register'],
            'multiple': metric_config.get('multiple', 1)
        }

    def setup_enum_collector(self, metric_config):
        metric_name = metric_config['metric_name']
        metric_type = metric_config['type']

        self.metrics_config[metric_name] = {
            'metric_type': metric_type,
            'metric': Enum(metric_name, metric_config['description'], states=metric_config['states']),
            'register': metric_config['register']
        }

    def setup_info_collector(self, metric_config):
        metric_name = metric_config['metric_name']
        metric_type = metric_config['type']

        self.metrics_config[metric_name] = {
            'metric_type': metric_type,
            'metric': Info(metric_name, metric_config['description']),
            'publish_info': metric_config['publish_info']
        }

    def publish(self, latest_scrape):
        try:
            for metric_name, config in self.metrics_config.items():
                if config['metric_type'] == 'Info':
                    publish = {}

                    for info in config['publish_info']:
                        publish[info['key']] = latest_scrape[info['register']]

                    self.metrics_config[metric_name]['metric'].info(publish)
                elif config['metric_type'] == 'Enum':
                    self.metrics_config[metric_name]['metric'].state(latest_scrape[config['register']])
                elif config['metric_type'] == 'Gauge':
                    self.metrics_config[metric_name]['metric'].set(
                        latest_scrape[config['register']] * config['multiple'])

            logging.debug("Prometheus-Published")
            return True
        except Exception as err:
            logging.error(f"Prometheus-Publishing: Error: {err}")
            return False

    def metrics(self):
        return generate_latest()
