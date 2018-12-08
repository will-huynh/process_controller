import logging
import tcp_log_socket

logging_socket = tcp_log_socket.local_logging_socket(__name__)
logger = logging_socket.logger

#Test method simulating a method with required arguments; division is used to test exception handling
def test_args(div1, div2):
    logger.info("Simulating a method with arguments and exceptions.")
    quotient = div1 / div2
    logger.info("Quotient is: {}".format(quotient))
    return quotient

#Test method simulating a method with no required arguments
def test_no_args():
    result = True
    logger.info("Simulating methods without arguments.")
    logger.info("Expected result: {}.".format(result))
    return result

#Test method simulating an argument with keyworded and optional arguments
def test_keyword(def_num=10, **kwargs):
    logger.info("Simulating methods with optional and keyworded arguments.")
    allowed_key = "key"
    value = False
    list_keys = list(kwargs.keys())
    logger.info("Default argument is {}.".format(def_num))
    for kw in list_keys:
        if kw == allowed_key:
            logger.info("Keyword found.")
            value = kwargs.pop(kw)
            logger.info("Keyword and value are {0} : {1}.".format(kw, value))
    return (def_num, value)
