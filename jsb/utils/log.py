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

format = "%(asctime)s - %(message)s - <%(threadName)s+%(module)s-%(funcName)s:%(lineno)s>"

try:
    import waveapi
except ImportError:
    try:
        filehandler = logging.handlers.TimedRotatingFileHandler(LOGDIR + os.sep + "jsb.log", 'midnight')
        formatter = logging.Formatter(format)
        filehandler.setFormatter(formatter)  
    except IOError:
        filehandler = None

## setloglevel function

def setloglevel(level_name="warn"):
    """ set loglevel to level_name. """
    if not level_name: return
    level = LEVELS.get(str(level_name).lower(), logging.NOTSET)
    root = logging.getLogger("")
    if root and root.handlers:
        for handler in root.handlers: root.removeHandler(handler)
    if root: logging.basicConfig(level=level, format=format)
    root.setLevel(level)
    try: import waveapi
    except ImportError:
        if filehandler: root.addHandler(filehandler)
    logging.warn("loglevel is %s (%s)" % (str(level), level_name))

def getloglevel():
    root = logging.getLogger("")
    return RLEVELS.get(root.level)
