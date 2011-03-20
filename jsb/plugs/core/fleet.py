# jsb/plugs/fleet.py
#
#

""" 
    The fleet makes it possible to run multiple bots in one running instance.
    It is a list of bots.

"""

## jsb imports

from jsb.lib.config import Config
from jsb.lib.threads import start_new_thread
from jsb.lib.fleet import getfleet, FleetBotAlreadyExists
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.utils.name import stripname
from jsb.utils.generic import waitforqueue

## basic imports

import os

## fleet-avail command

def handle_fleetavail(bot, ievent):
    """ show available fleet bots. """
    ievent.reply('available bots: ', getfleet().avail()) 

cmnds.add('fleet-avail', handle_fleetavail, 'OPER')
examples.add('fleet-avail', 'show available fleet bots', 'fleet-avail')

## fleet-connect command

def handle_fleetconnect(bot, ievent):

    """ connect a fleet bot to it's server. """
    try: botname = ievent.args[0]
    except IndexError:
        ievent.missing('<botname>')
        return
    try:
        fleet = getfleet()
        fleetbot = fleet.byname(botname)
        if fleetbot:
            start_new_thread(fleetbot.connect, ())
            ievent.reply('%s connect thread started' % botname)
        else:
            ievent.reply("can't connect %s .. trying enable" % botname)
            cfg = Config('fleet' + os.sep + stripname(botname) + os.sep + 'config')
            cfg['disable'] = 0
            cfg.save()
            bot = fleet.makebot(cfg.type, cfg.name, cfg)
            ievent.reply('enabled and started %s bot' % botname)
            start_new_thread(bot.start, ())
    except Exception, ex:
        ievent.reply(str(ex))

cmnds.add('fleet-connect', handle_fleetconnect, 'OPER', threaded=True)
examples.add('fleet-connect', 'connect bot with <name> to irc server', 'fleet-connect test')

## fleet-disconnect command

def handle_fleetdisconnect(bot, ievent):
    """ disconnect a fleet bot from server. """
    try: botname = ievent.args[0]
    except IndexError:
        ievent.missing('<botname>')
        return
    ievent.reply('exiting %s' % botname)
    try:
        fleet = getfleet()
        if fleet.exit(botname): ievent.reply("%s bot stopped" % botname)
        else: ievent.reply("can't stop %s bot" % botname)
    except Exception, ex: ievent.reply("fleet - %s" % str(ex))

cmnds.add('fleet-disconnect', handle_fleetdisconnect, 'OPER', threaded=True)
examples.add('fleet-disconnect', 'fleet-disconnect <name> .. disconnect bot with <name> from irc server', 'fleet-disconnect test')

## fleet-list command

def handle_fleetlist(bot, ievent):
    """ fleet-list .. list bot names in fleet. """
    ievent.reply("fleet: ", getfleet().list())

cmnds.add('fleet-list', handle_fleetlist, ['USER', 'GUEST'])
examples.add('fleet-list', 'show current fleet list', 'fleet-list')

## fleet-del command

def handle_fleetdel(bot, ievent):
    """ delete bot from fleet. """
    try: name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return
    try:
        if getfleet().delete(name): ievent.reply('%s deleted' % name)
        else: ievent.reply('%s delete failed' % name)
    except Exception, ex: ievent.reply(str(ex))

cmnds.add('fleet-del', handle_fleetdel, 'OPER', threaded=True)
examples.add('fleet-del', 'fleet-del <botname> .. delete bot from fleet list', 'fleet-del test')

## fleet-disable command

def fleet_disable(bot, ievent):
    """ disable a fleet bot. """
    if not ievent.rest:
        ievent.missing("list of fleet bots")
        return
    bots = ievent.rest.split()
    fleet = getfleet()
    for name in bots:
        bot = fleet.byname(name)
        if bot:
            bot.cfg['enable'] = 0
            bot.cfg.save()
            ievent.reply('disabled %s' % name)
            fleet.exit(name)
        else: ievent.reply("can't find %s bot in fleet" % name)

cmnds.add('fleet-disable', fleet_disable, 'OPER')
examples.add('fleet-disable', 'disable a fleet bot', 'fleet-disable local')

## fleet-enable command

def fleet_enable(bot, ievent):
    """ enable a fleet bot. """
    if not ievent.rest:
        ievent.missing("list of fleet bots")
        return
    bots = ievent.rest.split()
    fleet = getfleet()
    for name in bots:
        bot = fleet.byname(name)
        if bot:
            bot.cfg.load()
            bot.cfg['disable'] = 0
            bot.cfg.save()
            ievent.reply('enabled %s' % name)
            start_new_thread(bot.connect, ())
        elif name in fleet.avail():
            cfg = Config('fleet' + os.sep + stripname(name) + os.sep + 'config')
            cfg['disable'] = 0
            cfg.save()
            bot = fleet.makebot(cfg.type, cfg.name, cfg)
            if not bot: ievent.reply("can't make %s bot - %s" % (cfg.name, cfg.type)) ; return
            ievent.reply('enabled and started %s bot' % name)
            start_new_thread(bot.start, ())
        else: ievent.reply('no %s bot in fleet' % name)

cmnds.add('fleet-enable', fleet_enable, 'OPER', threaded=True)
examples.add('fleet-enable', 'enable a fleet bot', 'fleet-enable local')

def fleet_add(bot, ievent):
    """ add a fleet bot. """
    try:
        name, type, server, nick = ievent.rest.split()
    except ValueError: ievent.missing("<name> <type> <server>|<botjid> <nick>|<passwd>") ; return
    bots = ievent.rest.split()
    fleet = getfleet()
    bot = fleet.byname(name)
    if bot: event.reply("%s bot already exists" % name) ; return
    cfg = Config('fleet' + os.sep + stripname(name) + os.sep + 'config')
    cfg.disable = 0
    if type == "irc":
        cfg.port = 6667
        cfg.server = server
        cfg.nick = nick
    elif type in ["xmpp", "sxmpp"]:
        cfg.port = 4442
        cfg.host = server
        try: n, serv = cfg.host.split("@")
        except (ValueError, TypeError): pass
        cfg.server = serv
        cfg.password = nick
    cfg.save()
    bot = fleet.makebot(type, name, cfg)
    ievent.reply('enabled and started %s bot - %s' % (name, cfg.filename))
    start_new_thread(bot.start, ())

cmnds.add('fleet-add', fleet_add, 'OPER', threaded=True)
examples.add('fleet-add', 'add a fleet bot', 'fleet-add local irc localhost jsbtest')

def fleet_cmnd(bot, ievent):
    """ co cmnd on fleet bot(s). """
    try:
        (name, cmndtxt) = ievent.rest.split(' ', 1)
    except ValueError: ievent.missing("<name> <cmndstring>") ; return
    fleet = getfleet()
    if name == "all": do = fleet.list()
    else: do = [name, ]
    for botname in do:
        bot = fleet.byname(botname)
        if not bot: ievent.reply("%s bot is not in fleet" % botname) ; return
        result = bot.docmnd(ievent.userhost, ievent.channel, cmndtxt, wait=1, nooutput=True)
        if result: res = waitforqueue(result.outqueue, 60000)
        else: ievent.reply("no result")
        ievent.reply("[%s] %s" % (botname, ", ".join(res)))
    ievent.reply("done")

cmnds.add('fleet-cmnd', fleet_cmnd, 'OPER', threaded=True)
examples.add('fleet-cmnd', 'run cmnd on fleet bot(s)', '1) fleet-cmnd default-irc uptime 2) fleet-cmnd all uptime')
