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

## basic imports

import uuid
import time

## feedback command

def handle_feedback(bot, event):
    fleet = getfleet()
    feedbackbot = fleet.getfirstjabber()
    if not feedbackbot:
        if bot.isgae: cfg = LazyDict({"name": "feedbackbot-gae", "user": "feedback@jsonbot.org", "password": "givesomereply"})
        else: cfg = LazyDict({"name": "feedbackbot", "user": "feedback@jsonbot.org", "password": "givesomereply"})
        feedbackbot = fleet.makebot("sxmpp", cfg.name, config=cfg)
        if not feedbackbot: event.reply("can't make xmpp bot.") ; return
        feedbackbot.start()
        if not feedbackbot.cfg.password: feedbackbot.cfg.password = cfg['password'] ; feedbackbot.cfg.save()
    feedbackbot.cfg.disable = False
    event.reply("sending to bart@jsonbot.org ... ")
    feedbackbot.say("bart@jsonbot.org", event.rest)
    feedbackbot.cfg.disable = True
    feedbackbot.cfg.save()
    event.done()

cmnds.add("feedback", handle_feedback, ["OPER", "USER", "GUEST"])
examples.add("feedback", "send a message to bart@jsonbot.org", "feedback the bot is missing some spirit !")
