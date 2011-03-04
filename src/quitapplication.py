import signal
import pprint

def getsigdict():
    r = {}
    for name in dir(signal):
        if name.startswith("SIG"):
            r[getattr(signal, name)] = name
    return r
        
class QuitApplication(Exception):
    
    __signals = getsigdict()
    
    def __init__(self, signal):
        super(QuitApplication, self).__init__()
        self.__signal = signal
        
    @property
    def signal(self):
        return self.__signal
        
    @property
    def signalName(self):
        return self.__signals[self.__signal]
        