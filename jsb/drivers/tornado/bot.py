# jsb/drivers/tornado/bot.py
#
#

""" tornado web bot. """

## jsb imports

from jsb.lib.botbase import BotBase
from jsb.lib.outputcache import add
from jsb.utils.generic import toenc, fromenc, strippedtxt, stripcolor
from jsb.utils.url import re_url_match
from jsb.utils.timeutils import hourmin
from jsb.lib.channelbase import ChannelBase
from jsb.imports import getjson
from jsb.utils.exception import handle_exception

json = getjson()

## basic imports

import logging
import re
import cgi
import urllib
import time

## tornado import

import tornado.ioloop
import tornado.web

## WebBot class

class TornadoBot(BotBase):

    """ TornadoBot  just inherits from botbase for now. """

    def __init__(self, cfg=None, users=None, plugs=None, botname="tornado-bot", *args, **kwargs):
        BotBase.__init__(self, cfg, users, plugs, botname, *args, **kwargs)
        assert self.cfg
        self.type = u"tornado"
        self.isgae = False
        self.websockets = {}

    def _raw(self, txt, target, how, handler, end=u"<br>"):
        """  put txt to the client. """
        if not txt: return 
        txt = txt + end
        handler.write(txt)
        logging.debug("%s - out - %s" % (self.cfg.name, txt))

    def outnocb(self, channel, txt, how="background", event=None, origin=None, response=None, dotime=False, *args, **kwargs):
        txt = self.normalize(txt)
        if event and event.how != "background":
            logging.warn("%s - out - %s" % (self.cfg.name, txt))
        if "http://" in txt or "https://" in txt:
             for item in re_url_match.findall(txt):
                 logging.debug("web - raw - found url - %s" % item)
                 url = u'<a href="%s" onclick="window.open(\'%s\'); return false;">%s</a>' % (item, item, item)
                 try: txt = re.sub(item, url, txt)
                 except ValueError:  logging.error("web - invalid url - %s" % url)
        if response: self._raw(txt, event.target, event.how, event.handler)
        elif event: update_web(self, channel, txt, event.div, event.how or how)
        else: update_web(self, channel, txt, "content_div", how)
        self.benice(event)

    def normalize(self, txt):
        #txt = cgi.escape(txt)
        txt = stripcolor(txt)
        txt = txt.replace("&lt;br&gt;", "<br>")
        txt = txt.replace("&lt;b&gt;", "<b>")
        txt = txt.replace("&lt;/b&gt;", "</b>")
        txt = txt.replace("&lt;i&gt;", "<i>")
        txt = txt.replace("&lt;/i&gt;", "</i>")
        txt = txt.replace("&lt;h2&gt;", "<h2>")
        txt = txt.replace("&lt;/h2&gt;", "</h2>")
        txt = txt.replace("&lt;h3&gt;", "<h3>") 
        txt = txt.replace("&lt;/h3&gt;", "</h3>")
        txt = txt.replace("&lt;li&gt;", "<li>") 
        txt = txt.replace("&lt;/li&gt;", "</li>")
        #txt = txt.replace("&lt;", "<") 
        #txt = txt.replace("&gt;", ">")
        txt = strippedtxt(txt)
        return txt

    def reconnect(self): return True


def update_web(bot, channel, txt, div=None, how=None, end="<br>"):
        if not txt: return 
        #time.sleep(0.001)
        txt = txt + end
        outdict = {"target": div or "content_div", "result": txt, "how": how or "normal"}
        try: out = json.dumps(outdict)
        except Exception, ex: handle_exception() ; return
        logging.warn("%s - out - %s" % (bot.cfg.name, out))
        if not bot.websockets.has_key(channel): logging.warn("no %s in websockets dict" % channel) ; return
        for c in bot.websockets[channel]:
            time.sleep(0.1)
            c.write_message(out)
