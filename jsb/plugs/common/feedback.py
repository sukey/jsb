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
    feedbackbot = getfleet().getfirstjabber(bot.isgae)
    if not feedbackbot:
        cfg = {"botname": "feedbackbot", "user": "%s@jsonbot.org" % event.nick, "password": str(uuid.uuid4())}
        if not bot.isgae: feedbackbot = bot_factory.create("sxmpp", cfg)
        else: feedbackbot = bot_factory.create("xmpp", cfg)
    if not feedbackbot: event.reply("can't make xmpp bot.")
    else: event.reply("sending to bart@jsonbot.org ... ")
    if not bot.isgae: feedbackbot.connect(False)
    feedbackbot.say("bart@jsonbot.org", event.rest)
    time.sleep(5)
    event.done()

cmnds.add("feedback", handle_feedback, ["OPER", "USER", "GUEST"])
examples.add("feedback", "send a message to bart@jsonbot.org", "feedback the bot is missing some spirit !")
