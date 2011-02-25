from setproctitle import getproctitle, setproctitle

import settings
from server import Server

if __name__ == '__main__':
    setproctitle(settings.config['proctitle'])
    server = Server()
    server.run()