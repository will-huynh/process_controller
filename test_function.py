import logging
import tcp_log_socket

logging_socket = tcp_log_socket.local_logging_socket(__name__)
logger = logging_socket.logger

def test(num1, num2):
    quotient = num1 / num2
    logger.info("Quotient is: {}".format(quotient))
    return quotient
