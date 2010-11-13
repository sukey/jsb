# gozerlib/plugs/plug.py
#
#

""" plugin management. """

## gozerlib imports

from gozerlib.commands import cmnds
from gozerlib.examples import examples
from gozerlib.boot import default_plugins, plugin_packages, remove_plugin, update_mod

## plug-enable command

def handle_plugenable(bot, event):
    if not event.rest: event.missing("<plugin>") ; return
    mod = bot.plugs.whichmodule(event.rest)
    if not mod: event.reply("can't find module for %s" % event.rest) ; return
    event.reply("reloading and enabling %s" % mod)
    bot.plugs.enable(mod)
    bot.plugs.load(mod)
    update_mod(mod)
    event.done()

cmnds.add("plug-enable", handle_plugenable, ["OPER", ])
examples.add("plug-enable", "enable a plugin", "plug-enable commonplugs.rss")

## plug-disable command

def handle_plugdisable(bot, event):
    if not event.rest: event.missing("<plugin>") ; return
    mod = bot.plugs.whichmodule(event.rest)
    if mod in default_plugins: event.reply("can't remove a default plugin") ; return
    if not mod: event.reply("can't find module for %s" % event.rest) ; return
    event.reply("unloading and disabling %s" % mod)
    bot.plugs.unload(mod)
    bot.plugs.disable(mod)
    remove_plugin(mod)
    event.done()

cmnds.add("plug-disable", handle_plugdisable, ["OPER", ])
examples.add("plug-disable", "disable a plugin", "plug-disable commonplugs.rss")
