# jsb/lib/convore/event.py
#
#

""" convore event. """

## jsb imports

from jsb.lib.eventbase import EventBase
from jsb.utils.lazydict import LazyDict
from jsb.imports import getjson

## basic imports

import logging

## defines

json = getjson()


## ConvoreEvent

class ConvoreEvent(EventBase):
    """ Convore Event."""

    def parse(self, bot, message, root):
        m = LazyDict(message)
        self.root = LazyDict(root)
        m.kind.replace("-", "_")
        self.type = m.kind
        self.cbtype = "CONVORE"
        self.bottype = bot.type
        self.username = m.user['username']
        self.userhost = "%s_%s" % ("CONVORE_USER", self.username) 
        self._id = m._id
        self.userid = m.user['id']
        try: self.channel = m.topic['id'] ; self.groupchat = True
        except: self.channel = self.userid 
        self.auth = self.userhost
        self.txt = m.message
        self.nick = self.username
        logging.debug("convore - parsed event: %s" % self.dump())
        return self
