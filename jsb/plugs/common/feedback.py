# jsb/plugs/common/feedback.py
#
#

""" give feedback on the bot to dunker@jsonbot.org. connects to jsonbot.org if no jabber bot exists. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.fleet import getfleet
from jsb.lib.factory import bot_factory

## basic imports

import uuid
import time

## handle_feedback command

def handle_feedback(bot, event):
    feedbackbot = getfleet().byname("feedbackbot")
    if not feedbackbot:
        cfg = {"name": "feedbackbot", "user": "feedback@jsonbot.org", "password": "givesomereply"}
        if not bot.isgae: feedbackbot = bot_factory.create("sxmpp", cfg)
        else: feedbackbot = bot_factory.create("xmpp", cfg)
        feedbackbot.start()
        if not feedbackbot.cfg.password: feedbackbot.cfg.password = cfg['password'] ; feedbackbot.cfg.save()
    if not feedbackbot: event.reply("can't make xmpp bot.") ; return
    feedbackbot.cfg.enable = True
    event.reply("sending to bart@jsonbot.org ... ")
    feedbackbot.say("bart@jsonbot.org", event.rest)
    feedbackbot.cfg.enable = False
    event.done()

cmnds.add("feedback", handle_feedback, ["OPER", "USER", "GUEST"])
examples.add("feedback", "send a message to bart@jsonbot.org", "feedback the bot is missing some spirit !")
