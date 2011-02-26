import os
import logging
from logging.handlers import WatchedFileHandler

from setproctitle import getproctitle, setproctitle

import settings
from server import Server

if __name__ == '__main__':
    
    logFilePath = os.path.join(settings.config['logdir'], 'server.log')
    
    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)
    
    # We'll use a WatchedFileHandler and utilize some external application to
    # rotate the logs periodically
    handler = WatchedFileHandler(logFilePath)
    formatter = logging.Formatter(fmt='%(asctime)s|%(name)s|%(levelname)s|%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    
    logger.info('Log Server started')
    
    if 'proctitle' in settings.config:
        setproctitle(settings.config['proctitle'])
            
    server = Server()
    try:
        server.run()
    except Exception as ex:
        logger.error('Log Server encountered an exception %s', ex)
    finally:
        logger.info('Log Server stopped')