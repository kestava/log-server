import signal
import json
import os
import re
import pprint
import cStringIO
import logging
from logging.handlers import WatchedFileHandler
import time

import pika

import settings
from quitapplication import QuitApplication

class Server(object):
    
    __quitOn = [signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGINT]
    
    def __init__(self):
        self.__producer = settings.config['server-producer']
        self.__loggingLevel = settings.config['logging.level']
        self.__producers = settings.config['client-producers']
        self.__queueHost = settings.config['queue.host']
        self.__queueName = settings.config['queue.name']
        self.__queueRetryTimeout = settings.config['queue.retryTimeout']
        self.__loopTimeout = settings.config['loopTimeout']
        
        self.__setup_signal_handlers()
        [self.__create_producer_logger(i, j) for (i, j) in self.__producers.items()]
    
    def run(self):
        """
        Poll the queue at a certain interval for new messages.
        """
        try:
            while True:
                self.log('Loop start', level=logging.DEBUG)
                
                connection = None
                channel = None
                
                try:
                    connection = self.fresh_connection()
                    if connection.connection_open:
                        self.log('Got connection', level=logging.DEBUG)
                        channel = connection.channel()
                        
                        channel.queue_declare(
                            queue=self.__queueName,
                            durable=True,
                            exclusive=False,
                            auto_delete=False)
                    
                        channel.basic_consume(
                            consumer=self.__handle_delivery,
                            queue=self.__queueName)
                        
                        pika.asyncore_loop()
                        
                        self.log('Finished with connection', level=logging.DEBUG)
                    else:
                        self.log('No connection', level=logging.DEBUG)
                finally:
                    if not channel is None:
                        self.log('Closing channel', level=logging.DEBUG)
                        channel.close()
                        channel = None
                        
                    if not connection is None:
                        self.log('Closing connection', level=logging.DEBUG)
                        connection.close()
                        connection = None
                    
                time.sleep(self.__loopTimeout)
        except QuitApplication as e:
            self.log('Quitting application ({0})'.format(e.signalName))
        finally:
            self.log('Log Server stopped')
    
    def fresh_connection(self):
        self.log('Inside Server.fresh_connection', level=logging.DEBUG)
        return pika.AsyncoreConnection(
            parameters=pika.ConnectionParameters(host=self.__queueHost))
            
    def log(self, message, level=logging.INFO):
        """
        Write a message using the main application logger
        """
        logger = logging.getLogger()
        logger.log(level, message)
    
    def __handle_signal(self, signal_number, stack_frame):
        if signal_number in self.__quitOn:
            raise QuitApplication(signal=signal_number)
    
    def __setup_signal_handlers(self):
        for i in self.__quitOn:
            signal.signal(i, self.__handle_signal)
    
    def __create_producer_logger(self, producer, info):
        self.log('Inside Server.__create_producer_logger, Producer: {0}, Info: {1}'.format(producer, info), level=logging.DEBUG)
        logger = logging.getLogger(producer)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    
        # We'll use a WatchedFileHandler and utilize some external application to rotate the logs periodically
        logFilePath = os.path.join(settings.config['logdir'], '{0}.log'.format(producer))
        handler = WatchedFileHandler(logFilePath)
        handler.setLevel(info['logging.level'])
        formatter = logging.Formatter(fmt='%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(fmt='%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    def __write_to_log(self, message):
        def _write_string(output, message, name):
            if name in message:
                if output.getvalue() != '':
                    # append a separator before the value we're adding
                    output.write('|')
                output.write(str(message[name]))
                    
        if message['producer'] in self.__producers:
            s = cStringIO.StringIO()
            [_write_string(s, message, i) for i in ['host', 'pid', 'level_name', 'level_num', 'message']]
            try:
                logger = logging.getLogger(message['producer'])
                logger.log(level=message['level_num'], msg=s.getvalue())
            finally:
                s.close()
    
    def __handle_delivery(self, channel, method, header, body):
        self.log('Inside Server.__handle_delivery', level=logging.DEBUG)
        message = json.loads(body)
        self.__write_to_log(message)
            
        channel.basic_ack(delivery_tag=method.delivery_tag)