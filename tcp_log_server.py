import os
import json
import logging
import logging.handlers
import socketserver
import struct
from inspect import getsourcefile
from pythonjsonlogger import jsonlogger

"""Handler for a streaming logging request.

This basically logs the record using whatever logging policy is
configured locally.

This Python cookbook code was modified to unserialize and handle
incoming JSON logs.
"""
script_directory = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))

class LogRecordStreamHandler(socketserver.StreamRequestHandler):

    def unserialize_json(self, data):
        return json.loads(data)

    #Get name of logger from sending module and log records to a file.
    def handleLogRecord(self, record):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        TimedRotatingFileHandler = logging.handlers.TimedRotatingFileHandler(script_directory + "/test_log", when='h', interval=1) #change hardcoded log name
        formatter = jsonlogger.JsonFormatter('%(asctime)s - %(name)s - %(pathname)s -'
                            ' %(levelname)s - %(message)s')
        TimedRotatingFileHandler.setFormatter(formatter)
        if not len(logger.handlers):
            logger.addHandler(TimedRotatingFileHandler)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen + 2)
            chunk = chunk.split(bytes("  ", "utf-8"))
            json_log = chunk[1]
            obj = self.unserialize_json(json_log)
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)

class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver suitable for testing.
    """

    allow_reuse_address = True

    def __init__(self, host='localhost',
                 port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler=LogRecordStreamHandler):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort

def main():
    logging.basicConfig(
        format='%(relativeCreated)5d %(name)-8s %(asctime)-8s %(levelname)-8s %(message)s')
    tcpserver = LogRecordSocketReceiver()
    print('About to start TCP server...')
    tcpserver.serve_until_stopped()

if __name__ == '__main__':
    main()
