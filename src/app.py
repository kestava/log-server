import os
import logging
from logging.handlers import WatchedFileHandler

from setproctitle import getproctitle, setproctitle

import settings
from server import Server

def initialize_root_logger():
    logger = logging.getLogger()
    logger.setLevel(settings.config['logging.level'])
    
    # We'll use a WatchedFileHandler and utilize some external application to
    # rotate the logs periodically
    logFilePath = os.path.join(settings.config['logdir'], '{0}.log'.format(settings.config['server-producer']))
    handler = WatchedFileHandler(logFilePath)
    formatter = logging.Formatter(fmt='%(asctime)s|%(name)s|%(levelname)s|%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt='%(asctime)s|%(levelname)s|%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

if __name__ == '__main__':
    logger = initialize_root_logger()
    logger.info('Log Server started')
    
    if 'proctitle' in settings.config:
        setproctitle(settings.config['proctitle'])
            
    server = Server()
    server.run()