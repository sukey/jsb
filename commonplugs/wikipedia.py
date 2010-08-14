# plugs/wikipedia.py
#
#

""" query wikipedia .. use countrycode to select a country specific wikipedia. """

## gozerlib imports

from gozerlib.utils.url import geturl, striphtml
from gozerlib.utils.generic import splittxt, handle_exception, fromenc
from gozerlib.commands import cmnds
from gozerlib.examples import examples
from gozerlib.utils.rsslist import rsslist

## generic imports

from urllib import quote
import re
import logging

## defines

wikire = re.compile('start content(.*?)end content', re.M)

## functions

def searchwiki(txt, lang='en'):
    txt = txt.strip()
    for i in txt.split():
        if i.startswith('-'):
            if len(i) != 3:
                continue
            else:
                lang = i[1:]
            continue
    txt = txt.replace(u"-%s" % lang, '')
    txt = txt.capitalize()
    what = txt.replace(' ', '_')
    url = u'http://%s.wikipedia.org/wiki/Special:Export/%s' % (lang, \
quote(what.encode('utf-8')))
    url2 = u'http://%s.wikipedia.org/wiki/%s' % (lang, \
quote(what.encode('utf-8')))
    txt = getwikidata(url)
    if not txt:
        return ("", url2)
    if 'from other capitalisation' in txt:
        what = what.title()
        url = u'http://%s.wikipedia.org/wiki/Special:Export/%s' % (lang, \
quote(what.encode('utf-8')))
        url2 = u'http://%s.wikipedia.org/wiki/%s' % (lang, \
quote(what.encode('utf-8')))
        txt = getwikidata(url)
    if '#REDIRECT' in txt or '#redirect' in txt:
        redir = ' '.join(txt.split()[1:])
        url = u'http://%s.wikipedia.org/wiki/Special:Export/%s' % (lang, \
quote(redir.encode('utf-8')))
        url2 = u'http://%s.wikipedia.org/wiki/%s' % (lang, \
quote(redir.encode('utf-8')))
        txt = getwikidata(url)
    return (txt, url2)

def getwikidata(url):
    """ fetch wiki data """
    result = geturl(url)
    if not result:
        return
    res = rsslist(result)
    txt = ""
    for i in res:
        try:
            logging.warn(unicode(i))
            txt = i['text']
            break
        except:
            pass

    txt = re.sub('\[\[(.*?)\]\]', '<b>\g<1></b>', txt)
    txt = re.sub('{{(.*?)}}', '<i>\g<1></i>', txt)
    txt = re.sub('==(.*?)==', '<h3>\g<1></h3>', txt)
    txt = re.sub('=(.*?)=', '<h2>\g<1></h2>', txt)
    txt = re.sub('\*(.*?)\n', '<li>\g<1></li>', txt)
    txt = re.sub('\n\n', '<br><br>', txt)
    txt = re.sub('\s+', ' ', txt)
    txt = txt.replace('|', ' - ')
    return txt

## commands

def handle_wikipedia(bot, ievent):
    """ <what> .. search wikipedia. """
    if not ievent.rest:
        ievent.missing('<what>')
        return
    res = searchwiki(ievent.rest)
    if not res[0]:
        ievent.reply('no result found')
        return

    result = splittxt(res[0])
    if result:
        prefix = u'%s ===> ' % res[1]
        ievent.reply(prefix, result, dot="<br><br>")
    else:
        event.reply("no data found on %s" % event.rest)

cmnds.add('wikipedia', handle_wikipedia, ['USER', 'GUEST'])
examples.add('wikipedia', 'wikipedia ["-" <countrycode>] <what> .. search \
wikipedia for <what>','1) wikipedia gozerbot 2) wikipedia -nl bot')
