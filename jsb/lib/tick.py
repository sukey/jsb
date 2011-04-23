# jsb/tick.py
#
#

""" provide system wide clock tick. """

## jsb imports

from jsb.lib.threadloop import TimedLoop
from jsb.lib.eventbase import EventBase
from jsb.lib.callbacks import callbacks

## TickLoop class

class TickLoop(TimedLoop):


    def start(self, bot=None):
        """ start the loop. """
        self.bot = bot
        TimedLoop.start(self)

    def handle(self):
        """ send TICK events to callback. """
        event = EventBase()
        event.type = event.cbtype = 'TICK'
        callbacks.check(self.bot, event)

## global tick loop

tickloop = TickLoop('tickloop', 60)
