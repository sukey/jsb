# jsb/web/event.py
#
#

""" web event. """

## jsb imports

from jsb.lib.eventbase import EventBase
from jsb.utils.generic import splittxt, fromenc, toenc
from jsb.utils.xmpp import stripped
from jsb.lib.outputcache import add
from jsb.utils.url import getpostdata
from jsb.utils.exception import handle_exception
from jsb.lib.channelbase import ChannelBase
from jsb.imports import getjson
from jsb.utils.lazydict import LazyDict

json = getjson()

import tornado

## basic imports

import cgi
import logging
import re

## WebEvent class

class TornadoEvent(EventBase):

    def __init__(self, bot=None): 
        EventBase.__init__(self, bot=bot)
        self.bottype = "tornado"
        self.cbtype = "TORNADO"
        self.bot = bot

    def __deepcopy__(self, a):
        e = TornadoEvent()
        e.copyin(self)
        return e

    def parse(self, handler, request):
        """ parse request/response into a WebEvent. """
        #logging.warn(dir(handler))
        #logging.warn(dir(request))
        #logging.warn(request.arguments)
        #logging.warn(request.body)
        self.handler = handler
        self.request = request
        self.userhost = tornado.escape.xhtml_escape(handler.current_user)
        if not self.userhost: raise Exception("no current user.")
        try: how = request.arguments['how'][0]
        except KeyError: how = "background"
        if not how: how = "background"
        self.how = how
        if self.how == "undefined": self.how = "background"
        logging.warn("web - how is %s" % self.how)
        #self.webchan = request.headers.get('webchan')
        #input = request.headers.get('content') or request.headers.get('cmnd')
        if not input:
            try: input = request.arguments['content'] or request.arguments['cmnd']
            except KeyError: pass
        self.isweb = True
        logging.warn("input is %s" % input)
        self.origtxt = fromenc(input[0].strip(), self.bot.encoding)
        self.txt = self.origtxt
        self.usercmnd = self.txt and self.txt.split()[0]
        self.groupchat = False
        self.nick = self.userhost.split("@")[0]
        self.auth = fromenc(self.userhost)
        self.stripped = stripped(self.auth)
        self.domain = None
        self.channel = stripped(self.userhost)
        logging.debug(u'tornado - parsed - %s - %s' % (self.txt, self.userhost)) 
        self.makeargs()
        return self

    def parsesocket(self, handler, message):
        """ parse request/response into a WebEvent. """
        try: data = LazyDict(json.loads(message))
        except Exception, ex: logging.error("failed to parse data: %s - %s" % (message, str(ex))) ; return self
        logging.warn("incoming: %s" % message)
        self.div = data.target
        self.userhost = tornado.escape.xhtml_escape(handler.current_user)
        if not self.userhost: raise Exception("no current user.")
        self.isweb = True
        input = data.cmnd
        logging.warn("input is %s" % input)
        self.how = data.how
        self.origtxt = fromenc(input.strip(), self.bot.encoding)
        self.txt = self.origtxt
        self.usercmnd = self.txt and self.txt.split()[0]
        self.groupchat = False
        self.nick = self.userhost.split("@")[0]
        self.auth = fromenc(self.userhost)
        self.stripped = stripped(self.auth)
        self.domain = None
        self.channel = stripped(self.userhost)
        logging.debug(u'tornado - parsed - %s - %s' % (self.txt, self.userhost)) 
        self.makeargs()
        return self


    def reply(self, txt, result=[], event=None, origin="", dot=u", ", nr=600, extend=0, *args, **kwargs):
        """ reply to this event """#
        if self.checkqueues(result): return
        if not txt: return
        if self.how == "background":
            txt = self.bot.makeoutput(self.channel, txt, result, origin=origin, nr=nr, extend=extend, *args, **kwargs)
            self.bot.outnocb(self.channel, txt, self.how, response=self.response, event=self)
        else: self.bot.say(self.channel, txt, result, self.how or "normal", event=self)
        return self
