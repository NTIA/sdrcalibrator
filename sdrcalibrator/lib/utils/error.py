from __future__ import print_function
import sys


def error_out(logger, e):
    logger.force_new_line()
    logger.logln("", is_error=True)
    logger.logln("ERROR CODE: {}".format(e.err_code), is_error=True)
    if not e.err_head == "":
        logger.logln("!!! {} !!!".format(e.err_head), is_error=True)
    if not e.err_body == "":
        logger.logln(e.err_body, is_error=True)
    logger.logln("!!! Exiting prematurely !!!", is_error=True)
    sys.exit()


def error_out_pre_logger(e):
    print()
    print()
    print("ERROR CODE: {}".format(e.err_code))
    if not e.err_head == "":
        print("!!! {} !!!".format(e.err_head))
    if not e.err_body == "":
        print(e.err_body)
    print("!!! Exiting prematurely !!!")
    sys.exit()
