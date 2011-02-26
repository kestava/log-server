import signal
import json
import os
import re
import pprint
import cStringIO
import logging

import pika

import settings

class Server(object):
    
    __quitOn = [signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGINT]
    
    def __init__(self):
        self.__setup_signal_handlers()
        self.__producerLogs = self.__create_producer_logs()
    
    def run(self):
        queueName = settings.config['logging.queuename']
        params = pika.ConnectionParameters(host=settings.config['logging.host'])
        
        connection = pika.AsyncoreConnection(parameters=params)
        channel = connection.channel()
        
        channel.queue_declare(
            queue=queueName,
            durable=True,
            exclusive=False,
            auto_delete=False)
    
        channel.basic_consume(
            self.__handle_delivery,
            queue=queueName)
        
        try:
            pika.asyncore_loop()
        except KeyboardInterrupt:
            pass
        finally:
            channel.close()
            connection.close()
            self.log(
                'Close reason: {0}'.format(connection.connection_close.reply_text),
                logging.INFO)
            
    def log(self, message, level):
        """
        Write a message using the main application logger
        """
        logger = logging.getLogger()
        logger.log(level, message)
    
    def __handle_signal(self, signal_number, stack_frame):
        if signal_number in self.__quitOn:
            raise KeyboardInterrupt()
    
    def __setup_signal_handlers(self):
        [signal.signal(i, self.__handle_signal) for i in self.__quitOn]
    
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
        message = json.loads(body)
        producer = message['producer']
        if not producer in self.__producerLogs:
            self.__init_producer(producer)
            
        try:
            self.__write_to_log(message)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception, e:
            print(e)
        