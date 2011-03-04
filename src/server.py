import signal
import json
import os
import re
import pprint
import cStringIO
import logging
import time

import pika

import settings
from quitapplication import QuitApplication

class Server(object):
    
    __quitOn = [signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGINT]
    
    def __init__(self):
        self.__setup_signal_handlers()
        self.__producerLogs = self.__create_producer_logs()
        self.__queueHost = settings.config['queue.host']
        self.__queueName = settings.config['queue.name']
        self.__queueRetryTimeout = settings.config['queue.retryTimeout']
        self.__loopTimeout = settings.config['loopTimeout']
    
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
    
    def __create_producer_logs(self):
        o = {}
        r = re.compile('^([-\w]+)\.log$')
        for i in os.listdir(unicode(settings.config['logdir'])):
            a = r.match(i)
            if a:
                producer = a.group(1)
                producerFile = a.group()
                o[producer] = self.__create_producer_fileinfo(producerFile)
                
        return o
    
    def __create_producer_fileinfo(self, producerFile):
        return {
            'path': os.path.join(unicode(settings.config['logdir']), unicode(producerFile))
        }
    
    def __init_producer(self, producer):
        producerFile = '{0}.log'.format(producer)
        self.__producerLogs[producer] = self.__create_producer_fileinfo(producerFile)
        pprint.pprint(self.__producerLogs)
    
    def __write_to_log(self, message):
        s = cStringIO.StringIO()
        
        def _write_string(output, message, name, appendChar='|'):
            if name in message:
                output.write(str(message[name]))
                
                if not appendChar is None:
                    output.write(appendChar)
        
        _write_string(s, message, 'host')
        _write_string(s, message, 'pid')
        _write_string(s, message, 'level_name')
        _write_string(s, message, 'level_num')
        _write_string(s, message, 'message', None)
        
        s.write('\n')
        
        try:
            filename = self.__producerLogs[message['producer']]['path']
            with open(filename, 'a') as fp:
                fp.write(s.getvalue())
        finally:
            s.close()
    
    def __handle_delivery(self, channel, method, header, body):
        self.log('Inside Server.__handle_delivery', level=logging.DEBUG)
        message = json.loads(body)
        
        messageLevel = int(message['level_num'])
        
        logger = logging.getLogger()
        if messageLevel >= logger.level:
        
            producer = message['producer']
            if not producer in self.__producerLogs:
                self.__init_producer(producer)
            
            self.__write_to_log(message)
        
        else:
            print('Message skipped')
            
        channel.basic_ack(delivery_tag=method.delivery_tag)