# jsb/reboot.py
#
#

""" reboot code. """

## jsb imports

from jsb.lib.fleet import getfleet
from jsb.imports import getjson
json = getjson()

## basic imports

import os
import sys
import pickle
import tempfile
import logging

## reboot function

def reboot():
    """ reboot the bot. """
    logging.warn("reboot - rebooting")
    os.execl(sys.argv[0], *sys.argv)

## reboot_stateful function

def reboot_stateful(bot, ievent, fleet, partyline):
    """ reboot the bot, but keep the connections (IRC only). """
    logging.warn("reboot - doing statefull reboot")
    session = {'bots': {}, 'name': bot.cfg.name, 'channel': ievent.nick, 'partyline': []}
    for i in getfleet().bots:
        logging.warn("reboot - updating %s" % i.name)
        data = i._resumedata()
        if not data: continue
        session['bots'].update(data)
        if i.type == "sxmpp": i.exit()
    session['partyline'] = partyline._resumedata()
    sessionfile = tempfile.mkstemp('-session', 'jsb-')[1]
    json.dump(session, open(sessionfile, 'w'))
    getfleet().save()
    args = []
    if len(sys.argv) > 1:
        os.execl(sys.argv[0], sys.argv[0], '-r', sessionfile, *sys.argv[1:])
    else:
        os.execl(sys.argv[0], sys.argv[0], '-r', sessionfile)
