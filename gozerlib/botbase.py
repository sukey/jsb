# gozerlib/botbase.py
#
#

""" base class for all bots. """

## gozerlib imports

from eventhandler import mainhandler
from utils.lazydict import LazyDict
from plugins import plugs as coreplugs
from callbacks import callbacks, gn_callbacks
from eventbase import EventBase
from errors import NoSuchCommand, PlugsNotConnected, NoOwnerSet
from datadir import datadir
from commands import Commands
from config import cfg as mainconfig
from config import Config
from utils.pdod import Pdod
from channelbase import ChannelBase
from less import Less
from boot import boot
from utils.locking import lockdec
from exit import globalshutdown
from utils.generic import splittxt
from utils.trace import whichmodule

## basic imports

import time
import logging
import copy
import sys
import getpass
import os
import thread
import types

## define

cpy = copy.deepcopy

eventlock = thread.allocate_lock()
eventlocked = lockdec(eventlock)

## classes

class BotBase(LazyDict):

    def __init__(self, cfg=None, usersin=None, plugs=None, botname=None, *args, **kwargs):
        logging.debug("botbase - %s - %s" % (str(cfg), botname))
        LazyDict.__init__(self)
        self.starttime = time.time()
        self.isgae = False
        self.type = "base"
        self.status = "init"

        if botname:
            self.botname = botname
        else:
            self.botname = "default-%s" % str(type(self)).split('.')[-1][:-2]

        self.fleetdir = 'fleet' + os.sep + self.botname

        if cfg:
            self.cfg = cfg
            self.update(cfg)
        else:
            self.cfg = Config(self.fleetdir + os.sep + 'config')

        # set datadir to datadir/fleet/<botname>
        self.datadir = datadir + os.sep + self.fleetdir
        self.name = self.botname
        self.owner = self.cfg.owner
        if not self.owner:
            logging.warn("owner is not set in %s - using mainconfig" % self.cfg.cfile)
            self.owner = mainconfig.owner

        self.setusers(usersin)
        logging.warn("botbase - owner is %s" % self.owner)
        self.users.make_owner(self.owner)
        self._plugs = plugs or coreplugs 
        self.outcache = Less(1)
        self.userhosts = {}

        try:
            if not os.isdir(self.datadir):
               os.mkdir(self.datadir)
        except:
            pass

        self.setstate()

    def setstate(self, state=None):
        """ set state on the bot. """
        self.state = state or Pdod(self.datadir + os.sep + 'state')
        if self.state and not 'joinedchannels' in self.state.data:
            self.state.data.joinedchannels = []

    def setusers(self, users=None):
        """ set users on the bot. """
        if users:
            self.users = users
            return
        # initialize users 
        import gozerlib.users as u
        if not u.users:
            u.users_boot()
            self.users = u.users
        else:
            self.users = u.users

    def loadplugs(self, packagelist=[]):
        """ load plugins from packagelist. """
        self._plugs.loadall(packagelist)
        return self._plugs

    def start(self):
        """ start the mainloop of the bot. """
        # basic loop
        self.status == "running"

    def doevent(self, event):
        """ dispatch an event. """
        self.status = "dispatch"
        self.curevent = event
        go = False
        cc = "!"
        if event.chan:
            cc = event.chan.data.cc
        if not cc:
            cc = "!"
        logging.debug("cc for %s is %s" % (event.title or event.channel, cc))
        if event.txt and event.txt[0] in cc:
            event.txt = event.txt[1:]
            if event.txt:
                event.usercmnd = event.txt.split()[0]
            else:
                event.usercmnd = None
            event.makeargs()
            go = True
        starttime = time.time()
        e = cpy(event)
        if event.isremote:
            logging.debug('doing REMOTE callback')
            gn_callbacks.check(self, e)
        else:
            callbacks.check(self, e)

        if event.isremote and not event.remotecmnd:
            logging.debug("event is remote but not command .. not dispatching")
            return

        try:
            if go or event.bottype in ['web', 'xmpp', 'irc']:
                event.finish()
                result = self._plugs.dispatch(self, event)
            else:
                result =  []
        except NoSuchCommand:
            event.reply("no such command: %s" % event.usercmnd)
            result = []

        if event.chan:
            if event.chan.data.lastedited > starttime:
                event.chan.save()

        return result

    def ownercheck(self, userhost):
        """ check if provided userhost belongs to an owner. """
        if self.cfg and self.cfg.owner:
            if userhost in self.cfg.owner:
                return True

        return False

    def _raw(self, txt):
        """ override this. """ 
        print txt
        return self

    def say(self, channel, txt, result=[], event=None, *args, **kwargs):
        self._raw(self.makeresponse(txt, result))
        return self

    def outmonitor(self, origin, channel, txt, event=None):
        """ create an OUTPUT event with provided txt and send it to callbacks. """
        e = EventBase()
        if event:
            e.copyin(event)
        e.origin = origin
        e.ruserhost = event.userhost
        e.userhost = self.botname
        e.channel = channel
        e.txt = txt
        e.cbtype = 'OUTPUT'
        callbacks.check(self, e)

    def docmnd(self, origin, channel, txt, event=None):
        """ do a command. """
        e = EventBase()
        if event:
            e.copyin(event)
        e.bot = self
        e.origin = origin
        e.ruserhost = origin
        e.auth = origin
        e.userhost = origin
        e.channel = channel
        e.chan = ChannelBase(channel)
        e.txt = txt
        e.nick = e.userhost.split('@')[0]
        e.usercmnd = e.txt.split()[0]
        e.cbtype = 'DOCMND'
        e.makeargs()

        if self._plugs:
            try:
                return self._plugs.dispatch(self, e)
            except NoSuchCommand:
                print "no such command: %s" % e.usercmnd
        else:
            raise PlugsNotConnected()

    def less(self, who, what, nr=365):
        """ split up in parts of <nr> chars overflowing on word boundaries. """
        
        if type(what) == types.ListType:
            txtlist = what
        else:
            what = what.strip()
            txtlist = splittxt(what, nr)

        size = 0

        # send first block
        if not txtlist:
            logging.debug("can't split txt from %s" % what)
            return ["", ""]

        res = txtlist[0]

        # see if we need to store output in less cache
        result = ""
        if len(txtlist) > 2:
            logging.warn("addding %s lines to %s outputcache" % (len(txtlist), who))
            self.outcache.add(who, txtlist[1:])
            size = len(txtlist) - 2
            result = txtlist[1:2][0]
            if size:
                result += " (+%s)" % size
        else:
            if len(txtlist) == 2:
                result = txtlist[1]

        return [res, result]

    def join(self, channel, password, *args, **kwargs):
        """ join a channel. """
        pass

    def part(self, channel, *args, **kwargs):
        """ leave a channel. """
        pass

    def action(self, channel, txt, *args, **kwargs):
        """ send action to channel. """
        pass

    def reconnect(self, *args, **kwargs):
        """ do a server reconnect. """
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
        if self.state:
            self.state.save()

    def makeresponse(self, txt, result=[], dot=u", ", *args, **kwargs):
        """ create a response from a string and result list. """
        res = []
        # check if there are list in list

        for i in result:
            if type(i) == types.ListType or type(i) == types.TupleType:
                try:
                    res.append(dot.join(i))
                except TypeError:
                    res.extend(unicode(i))
            else:   
                res.append(unicode(i))

        if txt: 
            return txt + dot.join(res)   
        elif result:
            return dot.join(res)
        return ""   
