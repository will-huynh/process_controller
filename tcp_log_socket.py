import os
import logging, logging.handlers
import json
import hashlib
import struct
from inspect import getsourcefile

"""
Creates a TCP logging socket on the localhost. Modifies the default
Python logging socketHandler method, "MakePickle", to send JSON logs
instead of pickled logs.
"""
class local_logging_socket(object):

    #Initialize logger and socketHandler
    def __init__(self, module_name):
        self.logger = logging.getLogger(module_name)
        self.script_directory = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))
        if not len(self.logger.handlers):
            self.logger.setLevel(logging.INFO)
            self.socketHandler = logging.handlers.SocketHandler('localhost', logging.handlers.DEFAULT_TCP_LOGGING_PORT)
            self.socketHandler.makePickle = self.makePickle
            self.logger.addHandler(self.socketHandler)

    """
    Define a modification to the default logging socketHandler
    "makePickle" method. Dumps logs to a json format.
    """
    def makePickle(self, record):
        """
        Pickles the record in binary format with a length prefix, and
        returns it ready for transmission across the socket.
        """
        ei = record.exc_info
        if ei:
            # just to get traceback text into record.exc_text ...
            dummy = self.format(record)
        # See issue #14436: If msg or args are objects, they may not be
        # available on the receiving end. So we convert the msg % args
        # to a string, save it as msg and zap the args.
        d = dict(record.__dict__)
        d['msg'] = record.getMessage()
        d['args'] = None
        d['exc_info'] = None
        # Issue #25685: delete 'message' if present: redundant with 'msg'
        d.pop('message', None)
        s = json.dumps(d)
        #Create complete pickle to transmit; includes the length of the pickle and the pickle content in bytes
        slen = struct.pack(">L", len(s))
        return slen + bytes("  ", "utf-8") + bytes(s, "utf-8")
