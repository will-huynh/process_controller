import logging
import tcp_log_socket

logging_socket = tcp_log_socket.local_logging_socket(__name__)
logger = logging_socket.logger

def sum(num1, num2):
    sum = num1 + num2
    logger.info("Sum is: {}".format(sum))
    return sum
