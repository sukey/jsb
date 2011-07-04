# jsb/plugs/common/feedback.py
#
#

""" give feedback on the bot to dunker@jsonbot.org. connects to jsonbot.org if no jabber bot exists. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.fleet import getfleet
from jsb.lib.factory import bot_factory
from jsb.utils.lazydict import LazyDict
from jsb.utils.generic import waitforqueue

## basic imports

import uuid
import time

## feedback command

def handle_feedback(bot, event):
    if not event.rest and event.inqueue: payload = waitforqueue(event.inqueue, 2000)
    else: payload = event.rest 
    fleet = getfleet()
    feedbackbot = fleet.getfirstjabber()
    if not feedbackbot: event.reply("can't find an xmpp bot to send the feedback with") ; return
    #    if bot.isgae: cfg = LazyDict({"name": "feedbackbot-gae", "user": "feedback@jsonbot.org", "password": "givesomereply", "disable": False})
    #    else: cfg = LazyDict({"name": "feedbackbot", "user": "feedback@jsonbot.org", "password": "givesomereply", "disable": False})
    #    feedbackbot = fleet.makebot("sxmpp", cfg.name, config=cfg)
    #     if not feedbackbot: event.reply("can't make xmpp bot.") ; return
    #    #if not feedbackbot.started: feedbackbot.start()
    #    #if not feedbackbot.cfg.password: feedbackbot.cfg.password = cfg['password'] ; feedbackbot.cfg.save()
    feedbackbot.cfg.disable = False
    event.reply("sending to replies@jsonbot.org ... ")
    feedbackbot.say("replies@jsonbot.org", "%s send you this: %s" % (event.userhost, payload), event=event)
    #feedbackbot.cfg.disable = True
    feedbackbot.cfg.save()
    event.done()
    time.sleep(5)

cmnds.add("feedback", handle_feedback, ["OPER", "USER", "GUEST"], threaded=True)
examples.add("feedback", "send a message to replies@jsonbot.org", "1) admin-exceptions ! feedback 2) feedback the bot is missing some spirit !")
