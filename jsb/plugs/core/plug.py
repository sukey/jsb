# jsb/plugs/core/plug.py
#
#

""" plugin management. """

## jsb imports

from jsb.lib.commands import cmnds
from jsb.lib.examples import examples
from jsb.lib.boot import default_plugins, plugin_packages, remove_plugin, update_mod
from jsb.utils.exception import handle_exception, exceptionmsg
from jsb.lib.boot import savecmndtable, savepluginlist, update_mod
from jsb.lib.errors import NoSuchPlugin

## basic imports

import os
import logging

## plug-enable command

def handle_plugenable(bot, event):
    if not event.rest: event.missing("<plugin>") ; return
    mod = bot.plugs.getmodule(event.rest)
    if not mod: event.reply("can't find module for %s" % event.rest) ; return
    event.reply("reloading and enabling %s" % mod)
    bot.enable(mod)
    bot.plugs.reload(mod, force=True)
    event.done()

cmnds.add("plug-enable", handle_plugenable, ["OPER", ])
examples.add("plug-enable", "enable a plugin", "plug-enable jsb.plugs.common.rss")

## plug-disable command

def handle_plugdisable(bot, event):
    if not event.rest: event.missing("<plugin>") ; return
    mod = bot.plugs.getmodule(event.rest)
    if mod in default_plugins: event.reply("can't remove a default plugin") ; return
    if not mod: event.reply("can't find module for %s" % event.rest) ; return
    event.reply("unloading and disabling %s" % mod)
    bot.plugs.unload(mod)
    bot.disable(mod)
    event.done()

cmnds.add("plug-disable", handle_plugdisable, ["OPER", ])
examples.add("plug-disable", "disable a plugin", "plug-disable jsb.plugs.common.rss")

## plug-reload command

def handle_plugreload(bot, ievent):
    """ reload list of plugins. """
    try: pluglist = ievent.args
    except IndexError:
        ievent.missing('<list plugins>')
        return
    reloaded = []
    errors = []
    for plug in pluglist:
        modname = bot.plugs.getmodule(plug)
        if not modname: errors.append("can't find %s plugin" % plug) ; continue
        try:
            loaded = bot.plugs.reload(modname, force=True, showerror=True)
            for plug in loaded:
                reloaded.append(plug)
                logging.warn("reload - %s reloaded" % plug) 
        except NoSuchPlugin: errors.append("can't find %s plugin" % plug) ; continue
        except Exception, ex:
            if 'No module named' in str(ex) and plug in str(ex):
                logging.debug('reload - %s - %s' % (modname, str(ex)))
                continue
            errors.append(exceptionmsg())
    for modname in reloaded:
        if modname: update_mod(modname)
    if errors: ievent.reply('errors: ', errors)
    if reloaded: ievent.reply('reloaded: ', reloaded)

cmnds.add('plug-reload', handle_plugreload, 'OPER')
examples.add('plug-reload', 'reload <plugin>', 'reload core')
