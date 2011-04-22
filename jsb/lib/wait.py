# jsb/lib/waiter.py
#
#

""" wait for events. """

## jsb imports

from jsb.lib.runner import waitrunner
from jsb.utils.trace import whichmodule
from jsb.utils.exception import handle_exception

## basic imports

import logging
import copy
import types

## defines

cpy = copy.deepcopy

## Wait class

class Wait(object):

    """ 
        wait object contains a list of types to match and a list of callbacks to 
        call, optional list of userhosts to match the event with can be given. 
    """ 

    def __init__(self, cbtypes, cbs, userhosts=None, modname=None, event=None):
        if type(cbtypes) != types.ListType: cbtypes = [cbtypes, ]
        self.cbtypes = cbtypes
        self.userhosts = userhosts
        if type(cbs) != types.ListType: cbs= [cbs, ]
        self.cbs = cbs
        self.modname = modname
        self.origevent = event

    def check(self, bot, event):
        """ check whether event matches this wait object. if so call callbacks. """
        target = event.cmnd or event.cbtypes
        logging.debug("waiter - checking for %s - %s" % (target, self.cbtypes))
        if event.channel and self.origevent and not event.channel == self.origevent.channel:
            logging.warn("waiter - %s and %s dont match" % (event.channel, self.origevent.channel))
            return
        if target not in self.cbtypes: logging.warn("waiter - no match for %s found" % target) ; return
        if self.userhosts and event.userhost and event.userhost not in self.userhosts:
            logging.warn("waiter - no userhost matched")
            return
        self.docbs(bot, event)
        self.cbtypes.remove(event.cbtype)
        return event

    def docbs(self, bot, event):
        """ do the actual callback .. put callback on the waitrunner for execution. """
        logging.warn("%s - executing wait callbacks: %s" % (bot.cfg.name, str(self.cbs)))
        for cb in self.cbs:
            try: waitrunner.put(self.modname, cb, bot, event)
            except Exception, ex: handle_exception()

## Waiter class

class Waiter(object):

    """ list of wait object to match. """

    def __init__(self):
        self.waitlist = []

    def register(self, cbtypes, cbs, userhosts=None, event=None):
        """ add a wait object to the waitlist. """
        logging.warn("waiter - registering wait object: %s - %s" % (str(cbtypes), str(userhosts)))
        self.waitlist.append(Wait(cbtypes, cbs, userhosts, modname=whichmodule(), event=event))

    def check(self, bot, event):
        """ scan waitlist for possible wait object that match. """
        matches = []
        for wait in self.waitlist:
            result = wait.check(bot, event)
            if not wait.cbtypes: matches.append(wait)
        for w in matches: self.waitlist.remove(w)
        return matches

    def delete(self, removed):
        """ delete a list of wait items from the waitlist. """
        logging.warn("waiter - removing from waitlist: %s" % ", ".join(removed)) 
        for w in removed: self.waitlist.remove(w)

    def remove(self, modname):
        """ remove all waiter registered by modname. """
        removed = []
        for wait in self.waitlist:
            if wait.modname == modname: removed.append(wait)
        if removed: self.delete(removed)

## the global waiter object

waiter = Waiter()

