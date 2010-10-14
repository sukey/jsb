# plugs/gcalc.py
# encoding: utf-8
#
#

""" use google to calculate e.g. !gcalc 1 + 1 """

## gozerlib imports

from gozerlib.commands import cmnds
from gozerlib.examples import examples
from gozerlib.utils.url import useragent

from simplejson import loads

## basic imports

import urllib2

## gcalc command

def handle_gcalc(bot, ievent):
    """ use google calc . """
    if len(ievent.args) > 0: expr = " ".join(ievent.args).replace("+", "%2B").replace(" ", "+")
    else: ievent.missing('Missing an expression') ; return
    req = urllib2.Request("http://www.google.com/ig/calculator?hl=en&q=%s" % expr, None,  {'User-agent': useragent()})
    data = urllib2.urlopen(req).read()
    try:
        rhs = data.split("rhs")[1].split("\"")[1]
        lhs = data.split("lhs")[1].split("\"")[1]
        ievent.reply("%s = %s" % (lhs,rhs.replace('\\x26#215;', '*').replace('\\x3csup\\x3e', '**').replace('\\x3c/sup\\x3e', '')))
    except Exception, ex:
        ievent.reply(str(ex))    

cmnds.add('gcalc', handle_gcalc, ['USER', 'GUEST'])
examples.add('gcalc', 'calculate an expression using the google calculator', 'gcalc 1 + 1')
