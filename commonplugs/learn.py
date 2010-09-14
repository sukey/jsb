# commonplugs/learn.py
#
#

""" learn information items .. facts .. factoids. """

## gozerlib imports

from gozerlib.callbacks import callbacks
from gozerlib.commands import cmnds
from gozerlib.examples import examples
from gozerlib.utils.lazydict import LazyDict
from gozerlib.persist import PlugPersist

## basic imports

import logging

## commands

def handle_learn(bot, event):
    """" set an information item. """
    if not event.rest:
        event.missing("<item> is <description>")
        return
    try:
        (what, description) = event.rest.split(" is ")
    except ValueError:
        event.missing("<item> is <description>")
        return
        
    items = PlugPersist(event.channel)
    if not items.data:
        items.data = LazyDict()
    if not items.data.has_key(what):
        items.data[what] = []
    if description not in items.data[what]:
        items.data[what].append(description)
    items.save()
    event.reply("item added to %s database" % event.channel)

cmnds.add('learn', handle_learn, ['USER', 'OPER'])
cmnds.add('=', handle_learn, ['USER', 'OPER'])
examples.add('learn', 'learn the bot a description of an item.', "learn dunk is botpapa")

def handle_forget(bot, event):
    """" set an information item. """
    if not event.rest:
        event.missing("<item> and <match>")
        return
    try:
        (what, match) = event.rest.split(" and ", 2)
    except ValueError:
        event.missing("<item> and <match>")
        return
        
    items = PlugPersist(event.channel)
    if not items.data:
        items.data = LazyDict()
    if items.data.has_key(what):
        for i in range(len(items.data[what])):
            if match in items.data[what][i]:
                del items.data[what][i]                
                items.save()
                break
    event.reply("item removed from %s database" % event.channel)

cmnds.add('forget', handle_forget, ['USER', 'OPER'])
examples.add('forget', 'forget a description of an item.', "forget dunk and botpapa")

def handle_whatis(bot, event):
    items = PlugPersist(event.channel)
    if items.data.has_key(event.rest) and items.data[event.rest]:
        event.reply("%s is " % event.rest, items.data[event.rest], dot=", ")
    elif event.chan.data.info and event.chan.data.info.has_key(event.rest) and event.chan.info[event.rest]:
        event.reply("%s is " % event.rest, event.chan.data.info[event.rest], dot=", ")
    else:
        event.reply("no information known about %s" % event.rest)

cmnds.add('whatis', handle_whatis, ['USER', 'OPER', 'GUEST'])
cmnds.add('?', handle_whatis, ['USER', 'OPER'])
examples.add("whatis", "whatis learned about a subject", "whatis jsonbot")

def prelearn(bot, event):
    if event.usercmnd and not event.isremote:
        return True
    return False

def learncb(bot, event):
    items = PlugPersist(event.channel)
    try:
        target = event.usercmnd[1:]
    except IndexError:
        return
    if items.data.has_key(target):
        event.reply("%s is " % target, items.data[target], dot=", ")

callbacks.add("PRIVMSG", learncb, prelearn)
callbacks.add("MESSAGE", learncb, prelearn)
callbacks.add("DISPATCH", learncb, prelearn)
