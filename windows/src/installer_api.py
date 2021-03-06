import urllib2
import json
import os
import logging

from config import supported_configuration_versions
from application import Application
from action_handler import AsyncActionHandler

logger = logging.getLogger('peachy')


class ConfigException(Exception):
    def __init__(self, error_code, message):
        super(ConfigException, self).__init__(message)
        logger.error("{} - {}".format(error_code, message))
        self.error_code = error_code


class InstallerAPI(object):
    def __init__(self, config_url):
        logger.info("Fetching configuration from {}".format(config_url))
        self._config_url = config_url
        self._applications = []
        logger.info("Starting API")

    def _check_web_config(self, config):
        if "version" in config:
            if config["version"] not in supported_configuration_versions:
                raise ConfigException(10304,  "Configuration version too new installer upgrade required")
        else:
            raise ConfigException(10303, "Config is not valid")

    def _get_web_config(self):
        result = urllib2.urlopen(self._config_url)
        if result.getcode() != 200:
            raise ConfigException(10301, 'Connection unavailable')
        try:
            data = result.read()
            config = json.loads(data)
            self._check_web_config(config)
            return config
        except ConfigException:
            raise
        except Exception as ex:
            logger.error(ex)
            raise ConfigException(10302, 'Web data File Corrupt or damaged')

    def _get_file_config_path(self, app_id):
        profile = os.getenv('USERPROFILE')
        company_name = "Peachy"
        app_name = 'PeachyInstaller'
        return os.path.join(profile, 'AppData', 'Local', company_name, app_name, 'app-{}.json'.format(app_id))

    def _get_file_config(self, app_id):
        file_path = self._get_file_config_path(app_id)
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, 'r') as a_file:
                data = a_file.read()
                return json.loads(data)
        except IOError:
            raise ConfigException(10401, "Install File Inaccessable")
        except ValueError:
            raise ConfigException(10402, "Install File Corrupt or Damaged")

    def initialize(self):
        try:
            web_config = self._get_web_config()
            for web_app in web_config['applications']:
                file_app = self._get_file_config(web_app['id'])
                if file_app:
                    self._applications.append(Application.from_configs(web_app, file_app))
                else:
                    self._applications.append(Application.from_configs(web_app))
        except ConfigException as cfgex:
            return (False, cfgex.error_code, cfgex.message)
        return (True, "0", "Success")

    def get_items(self):
        return self._applications

    def get_item(self, id):
        return [app for app in self._applications if app.id == id][0]

    def process(self, id, base_install_path, action, status_callback=None, complete_callback=None):
        if action in ['install', 'remove', 'upgrade']:
            application = self.get_item(id)
            logger.info("Started {} of {} to {}".format(action, application.name, base_install_path))
            AsyncActionHandler(action, application, base_install_path, status_callback=status_callback, complete_callback=complete_callback).start()
        else:
            raise Exception("Nothing to do")
