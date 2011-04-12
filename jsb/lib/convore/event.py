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

    def parse(self, bot, message):
        m = LazyDict(message)
        logging.warn("convore - parsing event %s" % m)
        self.cbtype = "CONVORE"
        self.userhost = "%s_%s" % (bot.type, m.user['username']) 
        self.userid = m.user['id']
        self.channel = m.id
        self.type = m.kind
        self.auth = m.userhost
        return self
