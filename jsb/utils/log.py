# jsb/utils/log.py
#
#

""" log module. """

## basic imports

import logging
import logging.handlers
import os
import os.path
import getpass

## defines

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'warn': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL
         }

RLEVELS = {logging.DEBUG: 'debug',
           logging.INFO: 'info',
           logging.WARNING: 'warn',
           logging.ERROR: 'error',
           logging.CRITICAL: 'critical'
          }

try:
    import waveapi
except ImportError:
    LOGDIR = os.path.expanduser("~") + os.sep + ".jsb" + os.sep + "botlogs" # BHJTW change this for debian

try:
    ddir = os.sep.join(LOGDIR.split(os.sep)[:-1])
    if not os.path.isdir(ddir): os.mkdir(ddir)
except: pass

try:
    if not os.path.isdir(LOGDIR): os.mkdir(LOGDIR)
except: pass

format_short = "[!] %(asctime)-8s - %(module)+10s.%(funcName)-10s - %(message)s"
format = "[!] %(asctime)s.%(msecs)-13s - %(module)s.%(funcName)s:%(lineno)s - %(message)s - %(levelname)s - <%(threadName)s>"
datefmt = '%H:%M:%S'
formatter_short = logging.Formatter(format_short, datefmt=datefmt)
formatter = logging.Formatter(format, datefmt=datefmt)

try:
    import waveapi
except ImportError:
    try:
        filehandler = logging.handlers.TimedRotatingFileHandler(LOGDIR + os.sep + "jsb.log", 'midnight')
    except IOError:
        filehandler = None

## setloglevel function

def setloglevel(level_name="warn"):
    """ set loglevel to level_name. """
    if not level_name: return
    level = LEVELS.get(str(level_name).lower(), logging.NOTSET)
    root = logging.getLogger()
    root.setLevel(level)
    if root and root.handlers:
        for handler in root.handlers: root.removeHandler(handler)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    if level_name in ["debug",]: ch.setFormatter(formatter) ; filehandler.setFormatter(formatter)
    else: ch.setFormatter(formatter_short) ; filehandler.setFormatter(formatter_short)
    try: import waveapi
    except ImportError:
        root.addHandler(ch)
        if filehandler: root.addHandler(filehandler)
    logging.warn("loglevel is %s (%s)" % (str(level), level_name))

def getloglevel():
    import logging
    root = logging.getLogger()
    return RLEVELS.get(root.level)
