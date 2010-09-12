# gozerlib/plugs/test.py
# encoding: utf-8
#

""" test plugin. """

from gozerlib.utils.exception import exceptionmsg, handle_exception
from gozerlib.commands import cmnds
from gozerlib.examples import examples
from gozerlib.eventbase import EventBase
from gozerlib.users import users
from gozerlib.threads import start_new_thread
from gozerlib.socklib.utils.generic import waitforqueue
from gozerlib.runner import cmndrunner, defaultrunner

## basic imports

import time
import random
import copy
import logging

## defines

cpy = copy.deepcopy

donot = ['quit', 'reboot', 'shutdown', 'exit', 'delete', 'halt', 'upgrade', \
'install', 'reconnect', 'wiki', 'weather', 'sc', 'jump', 'disable', 'dict', \
'snarf', 'validate', 'popcon', 'twitter', 'tinyurl', 'whois', 'rblcheck', \
'wowwiki', 'wikipedia', 'tr', 'translate', 'serie', 'sc', 'shoutcast', 'mash', \
'gcalc', 'identi', 'mail', 'part', 'cycle', 'exception', 'fleet', 'ln', 'markov-learn', 'pit', 'bugtracker', 'tu', 'banner', 'test', 'cloud', 'dispatch', 'lns', 'loglevel', \
'cloneurl', 'clone', 'hb', 'rss-get', 'rss-sync']

errors = {}
teller = 0

def dummy(a, b=None):
    return ""

## functions

def dotest(bot, event):
    global teller
    global errors
    match = ""
    msg = cpy(event)
    if True:
        examplez = examples.getexamples()
        random.shuffle(examplez)
        for example in examplez:
            if match and match not in example:
                continue
            skip = False
            for dont in donot:
                if dont in example:
                    skip = True
            if skip:
                continue
            teller += 1
            event.reply('command: ' + example)
            try:
                msg.txt = "!" + example
                bot.docmnd(event.userhost, event.channel, example, msg)
            except Exception, ex:
                errors[example] = exceptionmsg()
    if errors:
        event.reply("there are %s errors .. " % len(errors))
        for cmnd, error in errors.iteritems():
            event.reply("%s - %s" % (cmnd, error))

## commands

def handle_testplugs(bot, event):
    """ test the plugins by executing all the available examples. """
    global teller
    try:
        loop = int(event.args[0])
    except (ValueError, IndexError):
        loop = 1
    try:
        threaded = event.args[1]
    except (ValueError, IndexError):
        threaded = 0

    threads = []
    teller = 0
    for i in range(loop):
        if threaded:
            threads.append(start_new_thread(dotest, (bot, event)))
        else:
            dotest(bot, event)

    if threads:
        for thread in threads:
            thread.join()
    event.reply('%s tests run' % teller)
    if errors:
        event.reply("there are %s errors .. " % len(errors))
        for cmnd, error in errors.iteritems():
            event.reply("%s - %s" % (cmnd, error))
    else:
        event.reply("no errors")

    event.outqueue.put_nowait(None)

cmnds.add('test-plugs', handle_testplugs, ['USER', ], threaded=True)
examples.add('test-plugs', 'test all plugins by running there examples', 'test-plugs')

def handle_forcedreconnect(bot, ievent):
    """ do a forced reconnect. """
    if bot.type == "sxmpp":
        bot.sock.shutdown(2)
    else:
        bot.sock.shutdown(2)

cmnds.add('test-forcedreconnect', handle_forcedreconnect, 'OPER')

def handle_forcedexception(bot, ievent):
    """ raise a exception. """
    raise Exception('test exception')

cmnds.add('test-forcedexception', handle_forcedexception, 'OPER')
examples.add('test-forcedexception', 'throw an exception as test', 'test-forcedexception')

def handle_testwrongxml(bot, ievent):
    """ try sending borked xml. """
    if not bot.type == "sxmpp":
        ievent.reply('only sxmpp')
        return
    ievent.reply('sending bork xml')
    bot._raw('<message asdfadf/>')

cmnds.add('test-wrongxml', handle_testwrongxml, 'OPER')

def handle_tojson(bot, ievent):
    """ dump the event to json. """
    ievent.reply(str(ievent.dump()))

cmnds.add('test-json', handle_tojson, 'OPER')
examples.add('test-json', "dump the event as json", "test-json")

def handle_testunicode(bot, ievent):
    """ send unicode test down the output paths. """
    outtxt = u"Đíť ìš éèñ ëņċøďıńğŧęŝţ· .. にほんごがはなせません .. ₀0⁰₁1¹₂2²₃3³₄4⁴₅5⁵₆6⁶₇7⁷₈8⁸₉9⁹ .. ▁▂▃▄▅▆▇▉▇▆▅▄▃▂▁ .. .. uǝʌoqǝʇsɹǝpuo pɐdı ǝɾ ʇpnoɥ ǝɾ .. AВы хотите говорить на русском языке, товарищ?"
    ievent.reply(outtxt)
    bot.say(ievent.channel, outtxt)

cmnds.add('test-unicode', handle_testunicode, 'OPER')
examples.add('test-unicode', 'test if unicode output path is clear', 'test-unicode')

def handle_testdocmnd(bot, ievent):
    """ call bot.docmnd(). """
    if ievent.rest:
        bot.docmnd(ievent.origin, ievent.channel, ievent.rest)
    else:
        ievent.missing("<cmnd>")

cmnds.add('test-docmnd', handle_testdocmnd, 'OPER')
examples.add('test-docmnd', 'test the bot.docmnd() method', 'test-docmnd version')
