# jsb/lib/convore/bot.py
#
#

""" convore bot. """

## jsb import

from jsb.lib.botbase import BotBase
from jsb.lib.errors import NotConnected
from jsb.lib.convore.event import ConvoreEvent
from jsb.utils.lazydict import LazyDict
from jsb.utils.exception import handle_exception
from jsb.imports import getjson, getrequests

## basic imports

import logging
import time

## defines

json = getjson()
requests = getrequests()

## ConvoreBot

class ConvoreBot(BotBase):

    """ The Convore Bot. """

    def __init__(self, cfg=None, usersin=None, plugs=None, botname=None, nick=None, *args, **kwargs):
        BotBase.__init__(self, cfg, usersin, plugs, botname, nick, *args, **kwargs)
        self.type = "convore"
        self.cursor = None
        if not self.state.has_key("namecache"): self.state["namecache"] = {}
        if not self.state.has_key("idcache"): self.state["idcache"] = {}

    def post(self, endpoint, data=None):
        logging.warn("%s - doing post on %s - %s" % (self.name, endpoint, data)) 
        assert self.username
        assert self.password
        self.auth = requests.AuthObject(self.username, self.password)
        res = requests.post("https://convore.com/api/%s" % endpoint, data or {}, auth=self.auth)
        logging.warn("%s - got result %s" % (self.name, res.content))
        if res.status_code == 200:
            logging.debug("%s - got result %s" % (self.name, res.content))
            return LazyDict(json.loads(res.content))
        else: logging.error("%s - %s - %s returned code %s" % (self.name, endpoint, data, res.status_code))

    def get(self, endpoint, data={}):
        logging.warn("%s - doing get on %s - %s" % (self.name, endpoint, data)) 
        self.auth = requests.AuthObject(self.username, self.password)
        url = "https://convore.com/api/%s" % endpoint
        logging.warn("%s - GET url is %s - data is %s" % (self.name, url, data)) 
        res = requests.get(url, data, auth=self.auth)
        if res.status_code == 200:
            logging.debug("%s - got result %s" % (self.name, res.content))
            return LazyDict(json.loads(res.content))
        logging.error("%s - %s - %s returned code %s" % (self.name, endpoint, data, res.status_code))
      
    def connect(self):
        logging.warn("%s - authing %s" % (self.name, self.username))
        r = self.get('account/verify.json')
        if r: logging.warn("%s - connected" % self.name) ;self.connectok.set()
        else: logging.warn("%s - auth failed - %s" % (self.name, r)) ; raise NotConnected(self.username)

    def outnocb(self, printto, txt, how="msg", event=None, origin=None, html=False, *args, **kwargs):
        txt = self.normalize(txt)
        logging.warn("%s - out - %s - %s" % (self.name, printto, txt))
        r = self.post("topics/%s/messages/create.json" % printto, data={"message": txt, "pasted": True})

    def discover(self, channel):
        res = self.get("groups/discover/search.json", {"q": channel })
        logging.warn("%s - discover result: %s" % (self.name, str(res)))
        for g in res.groups:
            group = LazyDict(g)
            self.state["namecache"][group.id] = group.name
            self.state["idcache"][group.name] = group.id
        self.state.save()
        return res.groups

    def join(self, channel, password=None):
        if channel not in self.state['joinedchannels']: self.state['joinedchannels'].append(channel) ; self.state.save()
        try: 
            self.join_id(self.state["idcache"][channel])
        except KeyError:  
            chans = self.discover(channel)
            self.join_id(chans[0]["id"], password)

    def join_id(self, id, password=None):
        logging.warn("%s - join %s" % (self.name, id))
        res = self.post("groups/%s/join.json" % id, {"group_id": id})
        return res

    def part(self, channel):
        logging.warn("%s - part %s" % (self.name, channel))
        res = self.post("groups/%s/leave.json" % channel, {"group_id": channel})
        if channel in self.state['joinedchannels']: self.state['joinedchannels'].remove(channel) ; self.state.save()
        return res

    def _readloop(self):
        self.connectok.wait(15)
        self.auth = requests.AuthObject(self.username, self.password)
        while not self.stopped:
            time.sleep(0.01)
            if self.cursor: result = self.get("live.json", {"cursor": self.cursor})
            else: result = self.get("live.json")
            logging.warn("%s - incoming - %s" % (self.name, str(result)))
            if not result: break
            if not result.messages: continue
            for message in result.messages:
                m = LazyDict(message)
                try:
                    method = getattr(self, "handle_%s" % m.kind)
                    method(m, result)
                #except (TypeError, AttributeError): continue
                except: handle_exception()

    def handle_message(self, message, root):
        self.cursor = message._id
        logging.warn("%s - cursor is %s" % (self.name, self.cursor))
        event = ConvoreEvent()
        event.parse(self, message, root)
        event.bind(self)
        self.doevent(event)
