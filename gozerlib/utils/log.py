# gozerlib/utils/log.py
#
#

""" log module. """

## basic imports

import logging
import logging.handlers
import os

## defines

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'warn': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

if not os.path.isdir("/var/log/jsonbot"): LOGDIR = os.getcwd() + os.sep + "jsonbot.logs"
else: LOGDIR = "/var/log/jsonbot"

try:
    if not os.path.isdir(LOGDIR): os.mkdir(LOGDIR)
except: pass

format = "%(asctime)s - %(message)s - %(threadName)s - %(module)s-%(funcName)s:%(lineno)s"

filehandler = logging.handlers.TimedRotatingFileHandler(LOGDIR + os.sep + "jsonbot.log", 'midnight')
formatter = logging.Formatter(format)
filehandler.setFormatter(formatter)  

## setloglevel function

def setloglevel(level_name):
    """ set loglevel to level_name. """
    level = LEVELS.get(level_name, logging.NOTSET)
    logging.basicConfig(level=level, format=format)
    root = logging.getLogger('')
    #if root.handlers:
    #    for handler in root.handlers: root.removeHandler(handler)
    root.addHandler(filehandler)
    root.setLevel(level)
    logging.info("loglevel is %s (%s)" % (str(level), level_name))
