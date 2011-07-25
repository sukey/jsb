# jsb/plugs/socket/chatlog.py
#
#

"""
    log irc channels to [hour:min] <nick> txt format, only 
    logging to files is supported right now. 

"""

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.callbacks import callbacks, remote_callbacks, last_callbacks, first_callbacks
from jsb.lib.persistconfig import PersistConfig
from jsb.utils.locking import lockdec
from jsb.utils.timeutils import hourmin
from jsb.lib.examples import examples
from jsb.utils.exception import handle_exception
from jsb.utils.lazydict import LazyDict
from jsb.lib.datadir import getdatadir
from jsb.utils.name import stripname
from jsb.utils.url import striphtml
from jsb.utils.format import formatevent, format_opt
from jsb.utils.log import init

## basic imports

import time
import os
import logging
import thread
from os import path
from datetime import datetime

## locks

outlock = thread.allocate_lock()
outlocked = lockdec(outlock)

## defines

cfg = PersistConfig()
cfg.define('channels', [])
cfg.define('format', 'log')
cfg.define('basepath', getdatadir())
cfg.define('nologprefix', '[nolog]')
cfg.define('nologmsg', '-= THIS MESSAGE NOT LOGGED =-')
cfg.define('backend', 'log')

logfiles = {}
backends = {}
stopped = False
db = None
eventstolog = ["OUTPUT", "PRIVMSG", "CONSOLE", "PART", "JOIN", "QUIT", "PRESENCE", "MESSAGE", "NOTICE", "MODE", "TOPIC", "KICK", "CONVORE", "TORNADO"]

## logging part

# BHJTW 21-02-2011 revamped to work with standard python logger

loggers = {}

def initlog(d):
    try: LOGDIR = d + os.sep + "chatlogs"
    except ImportError: LOGDIR = d + os.sep + "chatlogs"

    try:
        ddir = os.sep.join(LOGDIR.split(os.sep)[:-1])
        if not os.path.isdir(ddir): os.mkdir(ddir)   
    except: pass  

    try:
        if not os.path.isdir(LOGDIR): os.mkdir(LOGDIR)
    except: pass
    return LOGDIR

format = "%(message)s"

def timestr(dt):
    return dt.strftime(format_opt('timestamp_format'))   

## enablelogging function

def enablelogging(botname, channel):
    """ set loglevel to level_name. """
    global loggers
    LOGDIR = initlog(getdatadir())
    logging.warn("enabling on (%s,%s)" % (botname, channel))
    channel = stripname(channel)
    logname = "%s_%s" % (botname, channel)
    #if logname in loggers: logging.warn("there is already a logger for %s" % logname) ; return
    try:
        filehandler = logging.handlers.TimedRotatingFileHandler(LOGDIR + os.sep + logname + ".log", 'midnight')
        formatter = logging.Formatter(format)
        filehandler.setFormatter(formatter)  
    except IOError:
        filehandler = None
    chatlogger = logging.getLoggerClass()(logname)
    chatlogger.setLevel(logging.INFO)
    if chatlogger.handlers:
        for handler in chatlogger.handlers: chatlogger.removeHandler(handler)
    if filehandler: chatlogger.addHandler(filehandler) ; logging.info("%s - logging enabled on %s" % (botname, channel))
    else: logging.warn("no file handler found - not enabling logging.")
    global lastlogger
    lastlogger = chatlogger
    loggers[logname] = lastlogger

## do tha actual logging

@outlocked
def write(m): 
    """
      m is a dict with the following properties:
      datetime
      type : (comment, nick, topic etc..)
      target : (#channel, bot etc..)
      txt : actual message
      network
    """
    backend_name = cfg.get('backend', 'log')
    backend = backends.get(backend_name, log_write)
    if m.txt.startswith(cfg.get('nologprefix')): m.txt = cfg.get('nologmsg')
    backend(m)

def log_write(m):
    if stopped: return
    logname = "%s_%s" % (m.botname, stripname(m.target))
    timestamp = timestr(m.datetime)
    m.type = m.type.upper()
    line = '%(timestamp)s%(separator)s%(txt)s\n'%({
        'timestamp': timestamp, 
        'separator': format_opt('separator'),
        'txt': m.txt,
        'type': m.type
    })
    global loggers
    try: loggers[logname].info(line.strip())
    except KeyError: logging.warn("no logger available for channel %s" % logname)
    except Exception, ex: handle_exception()

backends['log'] = log_write

## log function

def log(bot, event):
    m = formatevent(bot, event, cfg.get("channels"))
    if m["txt"]: write(m)

## chatlog precondition

def prechatlogcb(bot, ievent):
    """
        Check if event should be logged.  QUIT and NICK are not channel
        specific, so we will check each channel in log().
    """
    if bot.isgae: return False
    if not cfg.channels: return False
    if not [bot.cfg.name, ievent.channel] in cfg.get('channels'): return False
    if not ievent.cbtype in eventstolog: return False
    if not ievent.msg: return True
    if ievent.cmnd in ('QUIT', 'NICK'): return True
    if ievent.cmnd == 'NOTICE':
        if [bot.cfg.name, ievent.arguments[0]] in cfg.get('channels'): return True
    return False

## chatlog callbacks

def chatlogcb(bot, ievent):
    log(bot, ievent)

## plugin-start

def init():
    global stopped
    stopped = False
    global loggers
    for (botname, channel) in cfg.get("channels"):
        enablelogging(botname, channel)  
    callbacks.add("PRIVMSG", chatlogcb, prechatlogcb)
    callbacks.add("JOIN", chatlogcb, prechatlogcb)
    callbacks.add("PART", chatlogcb, prechatlogcb)
    callbacks.add("NOTICE", chatlogcb, prechatlogcb)
    callbacks.add("QUIT", chatlogcb, prechatlogcb)
    callbacks.add("NICK", chatlogcb, prechatlogcb)
    callbacks.add("PRESENCE", chatlogcb, prechatlogcb)
    callbacks.add("MESSAGE", chatlogcb, prechatlogcb)
    callbacks.add("CONSOLE", chatlogcb, prechatlogcb)
    callbacks.add("CONVORE", chatlogcb, prechatlogcb)
    first_callbacks.add("OUTPUT", chatlogcb, prechatlogcb)
    return 1

## plugin-stop

def shutdown():
    global stopped
    stopped = True
    for file in logfiles.values():
        file.close()
    return 1

## chatlog-on command

def handle_chatlogon(bot, ievent):
    """ enable chatlog. """
    chan = ievent.channel
    enablelogging(bot.cfg.name, chan)
    if [bot.cfg.name, chan] not in cfg.get('channels'):
        cfg['channels'].append([bot.cfg.name, chan])
        cfg.save()
    ievent.reply('chatlog enabled on (%s,%s)' % (bot.cfg.name, chan))

cmnds.add('chatlog-on', handle_chatlogon, 'OPER')
examples.add('chatlog-on', 'enable chatlog on <channel> or the channel the commands is given in', '1) chatlog-on 2) chatlog-on #dunkbots')

## chatlog-off command

def handle_chatlogoff(bot, ievent):
    """ disable chatlog. """
    try: cfg['channels'].remove([bot.cfg.name, ievent.channel]) ; cfg.save()
    except ValueError: ievent.reply('chatlog is not enabled in (%s,%s)' % (bot.cfg.name, ievent.channel)) ; return
    try: del loggers["%s-%s" % (bot.cfg.name, stripname(ievent.channel))]
    except KeyError: pass
    except Exception, ex: handle_exception()
    ievent.reply('chatlog disabled on (%s,%s)' % (bot.cfg.name, ievent.channel))

cmnds.add('chatlog-off', handle_chatlogoff, 'OPER')
examples.add('chatlog-off', 'disable chatlog on <channel> or the channel the commands is given in', '1) chatlog-off 2) chatlog-off #dunkbots')

def handle_chatlogsearch(bot, event):
    if not event.rest: event.missing("<searchitem>") ; return
    result = []
    chatlogdir = getdatadir() + os.sep + "chatlogs"
    chan = event.options.channel or event.channel
    logs = os.listdir(chatlogdir)
    logs.sort()
    for f in logs:
        filename = stripname(f)
        if not chan[1:] in filename: continue
        for line in open(chatlogdir + os.sep + filename, 'r'):
            if event.rest in line: result.append(line)
    if result: event.reply("search results for %s" % event.rest, result, dot= " || ")
    else: event.reply("no result found for %s" % chan)

cmnds.add("chatlog-search", handle_chatlogsearch, ["OPER", "USER", "GUEST"])
examples.add("chatlog-search", "search the chatlogs of a channel.", "chatlog-search jsonbot")
