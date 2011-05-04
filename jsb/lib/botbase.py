# jsb/botbase.py
#
#

""" base class for all bots. """

## jsb imports

from jsb.utils.exception import handle_exception
from runner import defaultrunner, callbackrunner, waitrunner
from eventhandler import mainhandler
from jsb.utils.lazydict import LazyDict
from plugins import plugs as coreplugs
from callbacks import callbacks, first_callbacks, last_callbacks, remote_callbacks
from eventbase import EventBase
from errors import NoSuchCommand, PlugsNotConnected, NoOwnerSet, NameNotSet, NoEventProvided
from commands import Commands, cmnds
from config import Config
from jsb.utils.pdod import Pdod
from channelbase import ChannelBase
from less import Less, outcache
from boot import boot, getcmndperms, default_plugins
from jsb.utils.locking import lockdec
from exit import globalshutdown
from jsb.utils.generic import splittxt, toenc, fromenc, waitforqueue, strippedtxt, waitevents, stripcolor
from jsb.utils.trace import whichmodule
from fleet import getfleet
from aliases import getaliases
from jsb.utils.name import stripname
from tick import tickloop
from threads import start_new_thread, threaded
from morphs import inputmorphs, outputmorphs
from gatekeeper import GateKeeper
from wait import waiter

## basic imports

import time
import logging
import copy
import sys
import getpass
import os
import thread
import types
import threading
import Queue
import re

## defines

cpy = copy.deepcopy

## locks

reconnectlock = threading.RLock()
reconnectlocked = lockdec(reconnectlock)

lock = thread.allocate_lock()
locked = lockdec(lock)

## classes

class BotBase(LazyDict):

    """ base class for all bots. """

    def __init__(self, cfg=None, usersin=None, plugs=None, botname=None, nick=None, *args, **kwargs):
        logging.info("botbase - type is %s" % str(type(self)))
        if cfg: cfg = LazyDict(cfg)
        if cfg and not botname: botname = cfg.botname or cfg.name
        if not botname: botname = u"default-%s" % str(type(self)).split('.')[-1][:-2]
        if not botname: raise Exception("can't determine type")
        self.fleetdir = u'fleet' + os.sep + stripname(botname)
        self.cfg = Config(self.fleetdir + os.sep + u'config')
        if cfg: self.cfg.merge(cfg)
        self.cfg.name = botname
        if not self.cfg.name: raise Exception("botbase - name is not set in %s config file" % self.fleetdir)
        logging.info("botbase - name is %s" % self.cfg.name)
        LazyDict.__init__(self)
        self.ignore = []
        self.ids = []
        self.aliases = getaliases()
        self.curevent = None
        self.inqueue = Queue.Queue()
        self.outqueue = Queue.Queue()
        self.reconnectcount = 0
        self.stopped = False
        self.plugs = coreplugs
        self.gatekeeper = GateKeeper(self.cfg.name)
        self.gatekeeper.allow(self.user or self.jid or self.cfg.server or self.cfg.name)
        self.closed = False
        try:
            import waveapi
            self.isgae = True
            logging.debug("botbase - bot is a GAE bot (%s)" % self.cfg.name)
        except ImportError:
            self.isgae = False
            logging.debug("botbase - bot is a shell bot (%s)" % self.cfg.name)
        self.starttime = time.time()
        self.type = "base"
        self.status = "init"
        self.networkname = self.cfg.networkname or self.cfg.name or ""
        if self.cfg and not self.cfg.followlist: self.cfg.followlist = [] ; self.cfg.save()
        from jsb.lib.datadir import getdatadir
        datadir = getdatadir()
        self.datadir = datadir + os.sep + self.fleetdir
        self.owner = self.cfg.owner
        if not self.owner:
            logging.debug(u"owner is not set in %s - using mainconfig" % self.cfg.cfile)
            self.owner = Config().owner
        self.setusers(usersin)
        logging.info(u"botbase - owner is %s" % self.owner)
        self.users.make_owner(self.owner)
        self.outcache = outcache
        self.userhosts = {}
        self.connectok = threading.Event()
        self.reconnectcount = 0
        self.cfg.nick = nick or self.cfg.nick or u'jsb'
        try:
            if not os.isdir(self.datadir): os.mkdir(self.datadir)
        except: pass
        self.setstate()
        self.stopreadloop = False
        self.stopoutloop = False
        self.outputlock = thread.allocate_lock()
        self.outqueues = [Queue.Queue() for i in range(10)]
        self.tickqueue = Queue.Queue()
        self.encoding = self.cfg.encoding or "utf-8"
        self.cmndperms = getcmndperms()
        self.outputmorphs = outputmorphs
        self.inputmorphs = inputmorphs
        #fleet = getfleet(datadir)
        #if not fleet.byname(self.cfg.name): fleet.bots.append(self) ; 
        if not self.isgae:
            defaultrunner.start()
            callbackrunner.start()
            waitrunner.start()
            tickloop.start(self)

    def __deepcopy__(self, a):
        """ deepcopy an event. """  
        logging.debug("botbase - cpy - %s" % type(self))
        bot = BotBase(self.cfg) 
        bot.copyin(self)
        return bot

    def copyin(self, data):
        self.update(data)

    def _resume(self, data, botname, *args, **kwargs):
        pass

    def _resumedata(self):
        """ return data needed for resuming. """
        data = self.cfg
        try: data.fd = self.sock.fileno()
        except: pass
        return {self.cfg.name: data}

    def enable(self, modname):
        """ enable plugin given its modulename. """
        try: self.cfg.blacklist and self.cfg.blacklist.remove(modname)
        except ValueError: pass           
        if self.cfg.loadlist and modname not in self.cfg.loadlist: self.cfg.loadlist.append(modname)
        self.cfg.save()

    def disable(self, modname):
        """ disable plugin given its modulename. """
        if self.cfg.blacklist and modname not in self.cfg.blacklist: self.cfg.blacklist.append(modname)
        if self.cfg.loadlist and modname in self.cfg.loadlist: self.cfg.loadlist.remove(modname)
        self.cfg.save()

    def put(self, event):
        """ put an event on the worker queue. """
        if self.isgae:
            from jsb.drivers.gae.tasks import start_botevent
            start_botevent(self, event, event.speed)
        else: self.inqueue.put_nowait(event)

    def broadcast(self, txt):
        """ broadcast txt to all joined channels. """
        for chan in self.state['joinedchannels']:
            self.say(chan, txt)

    def _eventloop(self):
        """ fetch events from the inqueue and handle them. """
        logging.debug("%s - eventloop started" % self.cfg.name)
        while not self.stopped:
            event = self.inqueue.get()
            if not event: break
            self.doevent(event)
        logging.error("%s - eventloop stopped" % self.cfg.name)

    def _getqueue(self):
        """ get one of the outqueues. """
        go = self.tickqueue.get()
        q = []
        for index in range(len(self.outqueues)):
            if not self.outqueues[index].empty(): q.append(self.outqueues[index])
        return q

    def _outloop(self):
        """ output loop. """
        logging.debug('%s - starting output loop' % self.cfg.name)
        self.stopoutloop = 0
        while not self.stopped and not self.stopoutloop:
            queues = self._getqueue()
            if queues:
                for queue in queues:
                    try:
                        res = queue.get_nowait() 
                    except Queue.Empty: continue
                    if not res: continue
                    if not self.stopped and not self.stopoutloop:
                        logging.debug("%s - OUT - %s - %s" % (self.cfg.name, self.type, str(res))) 
                        self.out(*res)
                    time.sleep(0.01)
        logging.debug('%s - stopping output loop' % self.cfg.name)

    def putonqueue(self, nr, *args):
        """ put output onto one of the output queues. """
        self.outqueues[10-nr].put_nowait(args)
        self.tickqueue.put_nowait('go')

    def outputsizes(self):
        """ return sizes of output queues. """
        result = []  
        for q in self.outqueues:
            result.append(q.qsize())
        return result

    def setstate(self, state=None):
        """ set state on the bot. """
        self.state = state or Pdod(self.datadir + os.sep + 'state')
        if self.state and not 'joinedchannels' in self.state.data: self.state.data.joinedchannels = []

    def setusers(self, users=None):
        """ set users on the bot. """
        if users:
            self.users = users
            return
        import jsb.lib.users as u
        if not u.users: u.users_boot()
        self.users = u.users

    def loadplugs(self, packagelist=[]):
        """ load plugins from packagelist. """
        self.plugs.loadall(packagelist)
        return self.plugs

    def joinchannels(self):
        """ join channels. """
        time.sleep(Config().waitforjoin or 5)
        for i in self.state['joinedchannels']:
            try:
                logging.debug("%s - joining %s" % (self.cfg.name, i))
                channel = ChannelBase(i, self.cfg.name)
                if channel: key = channel.data.key
                else: key = None
                if channel.data.nick: self.ids.append("%s/%s" % (i, channel.data.nick))
                start_new_thread(self.join, (i, key))
                time.sleep(1)
            except Exception, ex:
                logging.warn('%s - failed to join %s: %s' % (self.cfg.name, i, str(ex)))
                handle_exception()

    def start(self, connect=True, join=True):
        """ start the mainloop of the bot. """
        if not self.isgae: 
            if connect: self.connect()
            start_new_thread(self._outloop, ())
            start_new_thread(self._eventloop, ())
            start_new_thread(self._readloop, ())
            if connect:
                self.connectok.wait(120)
                if self.connectok.isSet():
                    logging.warn('%s - logged on !' % self.cfg.name)
                    if join: start_new_thread(self.joinchannels, ())
                elif self.type not in ["console", "base"]: logging.warn("%s - failed to logon - connectok is not set" % self.cfg.name)
        self.status == "running"
        self.dostart(self.cfg.name, self.type)

    def doremote(self, event):
        """ dispatch an event. """
        if not event: raise NoEventProvided()
        event.forwarded = True
        logging.info("======== start handling REMOTE event ========")
        event.prepare(self)
        self.status = "callback"
        starttime = time.time()
        msg = "%s - %s - %s - %s" % (self.cfg.name, event.auth, event.how, event.cbtype)
        if event.how == "background": logging.debug(msg)
        else: logging.info(msg)
        logging.debug("botbase - remote - %s" % event.dump())
        if self.closed:
            if self.gatekeeper.isblocked(event.origin): return
        if event.status == "done":
            logging.debug("%s - event is done .. ignoring" % self.cfg.name)
            return
        self.reloadcheck(event)
        e0 = cpy(event)
        e0.speed = 1
        remote_callbacks.check(self, e0)
        logging.info("======== start handling REMOTE event ========")
        return

    def doevent(self, event):
        """ dispatch an event. """ 
        time.sleep(0.001)
        if not self.cfg: raise Exception("eventbase - cfg is not set .. can't handle event.") ; return
        if not event: raise NoEventProvided()
        try:
            if event.isremote(): self.doremote(event) ; return
            if event.type == "groupchat" and event.fromm in self.ids:
                logging.warn("%s - receiving groupchat from self (%s)" % (self.cfg.name, event.fromm))
                return
            event.txt = self.inputmorphs.do(fromenc(event.txt, self.encoding), event)
        except UnicodeDecodeError: logging.warn("%s - got decode error in input .. ingoring" % self.cfg.name) ; return
        logtxt = "%s - %s ======== start handling local event ======== %s" % (self.cfg.name, event.cbtype, event.userhost)
        if event.cbtype in ['NOTICE']: logging.warn("%s - %s - %s" % (self.cfg.name, event.nick, event.txt))
        else:
            try:
                int(event.cbtype)
                logging.debug(logtxt)
            except (ValueError, TypeError):
                if event.cbtype in ['PING', 'PRESENCE'] or event.how == "background": 
                    logging.debug(logtxt)
                else: logging.info(logtxt)
        event.bind(self)
        logging.debug("%s - event dump: %s" % (self.cfg.name, event.tojson()))
        self.status = "callback"
        starttime = time.time()
        if self.closed:
            if self.gatekeeper.isblocked(event.origin): return
        if event.status == "done":
            logging.debug("%s - event is done .. ignoring" % self.cfg.name)
            return
        self.reloadcheck(event)
        if event.msg or event.isdcc: event.speed = 2
        e1 = cpy(event)
        first_callbacks.check(self, e1)
        if not e1.stop: 
            callbacks.check(self, e1)
            if not e1.stop: last_callbacks.check(self, e1)
        event.callbackdone = True
        #if not self.isgae: import asyncore ; asyncore.loop(1)
        waiter.check(self, event)
        return event

    def ownercheck(self, userhost):
        """ check if provided userhost belongs to an owner. """
        if self.cfg and self.cfg.owner:
            if userhost in self.cfg.owner: return True
        return False

    def exit(self, stop=True):
        """ exit the bot. """ 
        logging.warn("%s - exit" % self.cfg.name)
        if not self.stopped: self.quit()
        if stop:
            self.stopped = True   
            self.stopreadloop = True  
            self.connected = False
        self.put(None)
        self.tickqueue.put_nowait('go')
        self.outqueue.put_nowait(None)
        self.shutdown()
        self.save()

    def _raw(self, txt, *args, **kwargs):
        """ override this. """ 
        logging.debug(u"%s - out - %s" % (self.cfg.name, txt))
        print txt

    def makeoutput(self, printto, txt, result=[], nr=375, extend=0, dot=", ", origin=None, *args, **kwargs):
        if not txt: return ""
        txt = self.makeresponse(txt, result, dot)
        res1, nritems = self.less(origin or printto, txt, nr+extend)
        return res1

    def out(self, printto, txt, how="msg", event=None, origin=None, html=False, *args, **kwargs):
        self.outnocb(printto, txt, how, event=event, origin=origin, html=html, *args, **kwargs)
        self.outmonitor(origin, printto, txt, event=event)

    write = out

    def outnocb(self, printto, txt, how="msg", event=None, origin=None, html=False, *args, **kwargs):
        self._raw(txt)

    writenocb = outnocb

    def say(self, channel, txt, result=[], how="msg", event=None, nr=375, extend=0, dot=", ", *args, **kwargs):
        if event and event.userhost in self.ignore: logging.warn("%s - ignore on %s - no output done" % (self.cfg.name, event.userhost)) ; return
        if event and event.nooutput:
            logging.debug("%s - event has nooutput set, not outputing" % self.cfg.name)
            if event: event.outqueue.put_nowait(txt)
            return
        if event and event.how == "msg":
             if self.type == "irc": target = event.nick
             else: target = channel
        else: target = channel
        if event and event.showall: txt = self.makeresponse(txt, result, dot, *args, **kwargs)
        else: txt = self.makeoutput(channel, txt, result, nr, extend, dot, origin=target, *args, **kwargs)
        if txt:
            if event:
                event.resqueue.put_nowait(txt)
                event.outqueue.put_nowait(txt)
                if event.path != None and not self.cfg.name in event.path: event.path.append(self.cfg.name)
            txt = self.outputmorphs.do(txt, event)
            self.out(target, txt, how, event=event, origin=target, *args, **kwargs)
        if event: event.result.append(txt)

    def saynocb(self, channel, txt, result=[], how="msg", event=None, nr=375, extend=0, dot=", ", *args, **kwargs):
        txt = self.makeoutput(channel, txt, result, nr, extend, dot, *args, **kwargs)
        if event and not self.cfg.name in event.path: event.path.append(self.cfg.name)
        txt = self.outputmorphs.do(txt, event)
        if txt:
            self.outnocb(channel, txt, how, event=event, origin=channel, *args, **kwargs)
            if event: event.result.append(txt)

    def less(self, printto, what, nr=365):
        """ split up in parts of <nr> chars overflowing on word boundaries. """
        if type(what) == types.ListType: txtlist = what
        else:
            what = what.strip()
            txtlist = splittxt(what, nr)
        size = 0
        if not txtlist:   
            logging.debug("can't split txt from %s" % what)
            return ["", ""]
        res = txtlist[0]
        length = len(txtlist)
        if length > 1:
            logging.info("addding %s lines to %s outputcache" % (len(txtlist), printto))
            outcache.set(u"%s-%s" % (self.cfg.name, printto), txtlist[1:])
            res += "<b> - %s more</b>" % (length - 1) 
        return [res, length]

    def join(self, channel, password, *args, **kwargs):
        """ join a channel. """
        pass

    def part(self, channel, *args, **kwargs):
        """ leave a channel. """
        pass

    def action(self, channel, txt, event=None, *args, **kwargs):
        """ send action to channel. """
        pass

    def reconnect(self):
        """ reconnect to the server. """
        if self.stopped: logging.warn("%s - bot is stopped .. not reconnecting" % self.cfg.name) ; return
        try:
            try: self.exit()
            except Exception, ex: handle_exception()
            self.reconnectcount += 1
            logging.warn('%s - reconnecting .. sleeping %s seconds' % (self.cfg.name, self.reconnectcount*15))
            time.sleep(self.reconnectcount * 15)   
            self.doreconnect()
        except Exception, ex: 
            handle_exception()

    def doreconnect(self):
        self.start(connect=True)

    def invite(self, *args, **kwargs):
        """ invite another user/bot. """
        pass

    def donick(self, nick, *args, **kwargs):
        """ do a nick change. """
        pass

    def shutdown(self, *args, **kwargs):
        """ shutdown the bot. """
        pass

    def quit(self, reason="", *args, **kwargs):
        """ close connection with the server. """
        pass

    def connect(self, reconnect=True, *args, **kwargs):
        """ connect to the server. """
        pass

    def names(self, channel, *args, **kwargs):
        """ request all names of a channel. """
        pass

    def save(self, *args, **kwargs):
        """ save bot state if available. """
        if self.state: self.state.save()

    def makeresponse(self, txt, result=[], dot=", ", *args, **kwargs):
        """ create a response from a string and result list. """
        res = []
        dres = []
        if type(txt) == types.DictType or type(txt) == types.ListType:
            result = txt
        if type(result) == types.DictType:
            for key, value in result.iteritems():
                dres.append(u"%s: %s" % (key, unicode(value)))
        if dres: target = dres
        else: target = result
        if target:
            txt = u"<b>" + txt + u"</b>"
            for i in target:
                if not i: continue
                if type(i) == types.ListType or type(i) == types.TupleType:
                    try:
                        res.append(dot.join(i))
                    except TypeError: res.extend(i)
                elif type(i) == types.DictType:
                    for key, value in i.iteritems():
                        res.append(u"%s: %s" % (key, unicode(value)))
                else: res.append(unicode(i))
        ret = ""
        if txt: ret = unicode(txt) + dot.join(res)   
        elif res: ret =  dot.join(res)
        if ret: return ret
        return ""
    
    def reloadcheck(self, event, target=None):
        """ check if plugin need to be reloaded for callback, """
        plugloaded = []
        target = target or event.cbtype or event.cmnd
        try:
            from boot import getcallbacktable   
            p = getcallbacktable()[target]
        except KeyError:
            logging.debug("botbase - can't find plugin to reload for %s" % event.cmnd)
            return
        logging.debug("%s - checking %s" % (self.cfg.name, unicode(p)))
        for name in p:
            if name in self.plugs:
                logging.debug("%s - %s is already loaded" % (self.cfg.name, name))
                continue
            if name in default_plugins: pass
            elif self.cfg.blacklist and name in self.cfg.blacklist:
                logging.warn("%s - %s is in blacklist" % (self.cfg.name, name))
                continue
            elif self.cfg.loadlist and name not in self.cfg.loadlist:
                logging.warn("%s - %s is not in loadlist" % (self.cfg.name, name))
                continue
            logging.info("%s - on demand reloading of %s" % (self.cfg.name, name))
            try:
                mod = self.plugs.reload(name, force=True, showerror=False)
                if mod: plugloaded.append(mod) ; continue
            except Exception, ex: handle_exception(event)
        return plugloaded

    def send(self, *args, **kwargs):
        pass

    def sendnocb(self, *args, **kwargs):
        pass

    def normalize(self, what):
        """ convert markup to IRC bold. """
        txt = strippedtxt(what, ["\002", "\003"])
        txt = re.sub("\s+", " ", what)
        txt = stripcolor(txt)
        txt = txt.replace("\002", "*")
        txt = txt.replace("<b>", "")
        txt = txt.replace("</b>", "")
        txt = txt.replace("<i>", "")
        txt = txt.replace("</i>", "")
        txt = txt.replace("&lt;b&gt;", "*")
        txt = txt.replace("&lt;/b&gt;", "*")
        txt = txt.replace("&lt;i&gt;", "")
        txt = txt.replace("&lt;/i&gt;", "")
        return txt

    def dostart(self, botname=None, bottype=None, *args, **kwargs):
        """ create an START event and send it to callbacks. """
        e = EventBase()
        e.bot = self
        e.botname = botname or self.cfg.name
        e.bottype = bottype or self.type
        e.origin = e.botname
        e.ruserhost = self.cfg.name +'@' + self.cfg.uuid
        e.userhost = e.ruserhost
        e.channel = botname
        e.origtxt = str(time.time())
        e.txt = e.origtxt
        e.cbtype = 'START'
        e.botoutput = False
        e.ttl = 1
        e.nick = self.cfg.nick or self.cfg.name
        self.doevent(e)
        logging.debug("%s - START event send to callbacks" % self.cfg.name)

    def outmonitor(self, origin, channel, txt, event=None):
        """ create an OUTPUT event with provided txt and send it to callbacks. """
        if event: e = cpy(event)
        else: e = EventBase()
        #e = EventBase()
        if e.status == "done":
            logging.debug("%s - outmonitor - event is done .. ignoring" % self.cfg.name)
            return
        e.bot = self
        e.origin = origin
        e.ruserhost = self.cfg.name +'@' + self.cfg.uuid
        e.userhost = e.ruserhost
        e.auth = e.userhost
        e.channel = channel
        e.origtxt = txt
        e.txt = txt
        e.cbtype = 'OUTPUT'
        e.botoutput = True
        e.nodispatch = True
        e.ttl = 1
        e.nick = self.cfg.nick or self.cfg.name
        e.bind(self)
        first_callbacks.check(self, e)

    def docmnd(self, origin, channel, txt, event=None, wait=0, showall=False, nooutput=False):
        """ do a command. """
        if event: e = cpy(event)
        else: e = EventBase()
        e.cbtype = "CMND"
        e.bot = self
        e.origin = origin
        e.ruserhost = origin
        e.auth = origin
        e.userhost = origin
        e.channel = channel
        e.txt = unicode(txt)
        e.nick = e.userhost.split('@')[0]
        e.usercmnd = e.txt.split()[0]
        #e.iscommand = True
        #e.iscallback = False
        e.allowqueues = True
        e.onlyqueues = False
        e.closequeue = True
        e.showall = showall
        e.nooutput = nooutput
        e.bind(self)
        #if wait: e.direct = True ; e.nothreads = True ; e.wait = wait
        if cmnds.woulddispatch(self, e) or e.txt[0] == "?": return self.doevent(e)
        #self.put(e)
        #return e

    def putevent(self, origin, channel, txt, event=None, wait=0, showall=False, nooutput=False):
        """ insert an event into the callbacks chain. """
        assert origin
        if event: e = cpy(event)
        else: e = EventBase()
        e.cbtype = "CMND"
        e.bot = self
        e.origin = origin
        e.ruserhost = origin
        e.auth = origin
        e.userhost = origin
        e.channel = channel
        e.txt = unicode(txt)
        e.nick = e.userhost.split('@')[0]
        e.usercmnd = e.txt.split()[0]
        e.iscommand = False
        #e.iscallback = False
        e.allowqueues = True
        e.onlyqueues = False
        e.closequeue = True
        e.showall = showall
        e.nooutput = nooutput
        e.wait = wait
        e.bind(self)
        self.put(e)
        return e

    def execstr(self, origin, channel, txt, event=None, wait=0, showall=False, nooutput=False):
        e = self.putevent(origin, channel, txt, event, wait, showall, nooutput)
        waitevents([e, ])
        return e.result

    def settopic(self, channel, txt):
        pass

    def gettopic(self, channel):
        pass
