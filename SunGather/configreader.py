import os


class Configreader:

    ENV_PREFIX = 'SUNGATHER_'

    def __init__(self, config, prefix=None):
        self.config = config
        self.prefix = prefix

    def get(self, key, default):
        env = self.ENV_PREFIX + self.prefix.upper() + '_' + key.upper()
        return os.getenv(env, self.config.get(key, default))
