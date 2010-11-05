# gaelib/xmpp/event.py
#
#

""" an xmpp event. """

## gozerlib imports

from gozerlib.eventbase import EventBase
from gozerlib.utils.xmpp import stripped, resource
from gozerlib.utils.lazydict import LazyDict
from gozerlib.gae.utils.auth import checkuser
from gozerlib.utils.generic import  strippedtxt

## xmpp import

from gozerlib.contrib.xmlstream import XMLescape, XMLunescape

## basic imports

import cgi
import logging
import re

## XMPPEvent class

class XMPPEvent(EventBase):

    """ an XMPP event. """

    def __init__(self, bot=None): 
        EventBase.__init__(self)
        self.bottype = "xmpp"
        self.cbtype = 'MESSAGE'
        self.bot = bot

    def __deepcopy__(self, a):
        """ make a deepcopy of this XMPPEvent. """
        return XMPPEvent().copyin(self)

    def parse(self, request, response):
        """ parse incoming request/response into a XMPPEvent. """
        self.copyin(LazyDict(request.POST))
        (userhost, user, u, nick) = checkuser(response, request)
        self.userhost = self['from']
        self.origin = self.channel
        if user: self.auth = user.email()
        else: self.auth = stripped(self.userhost)
        logging.info('xmpp - auth is %s' % self.auth)
        self.resource = resource(self['from'])
        self.jid = self['from']
        self.to = stripped(self['to'])
        self.channel = stripped(self.userhost)
        self.stripped = stripped(self.userhost)
        self.nick = self.stripped.split("@")[0]
        self.origin = self.channel
        input = self.body or self.stanza
        input = input.strip()
        self.origtxt = input
        self.txt = input
        self.usercmnd = self.txt.split()[0].lower()
        logging.debug(u'xmpp - in - %s - %s' % (self.userhost, self.txt))
        return self

