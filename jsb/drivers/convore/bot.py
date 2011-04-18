# jsb/lib/convore/bot.py
#
#

""" convore bot. """

## jsb import

from jsb.lib.botbase import BotBase
from jsb.lib.errors import NotConnected
from jsb.drivers.convore.event import ConvoreEvent
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
        self.nick = cfg.username or "jsonbot"

    def post(self, endpoint, data=None):
        logging.debug("%s - doing post on %s - %s" % (self.name, endpoint, data)) 
        assert self.username
        assert self.password
        self.auth = requests.AuthObject(self.username, self.password)
        res = requests.post("https://convore.com/api/%s" % endpoint, data or {}, auth=self.auth)
        logging.debug("%s - got result %s" % (self.name, res.content))
        if res.status_code == 200:
            logging.debug("%s - got result %s" % (self.name, res.content))
            return LazyDict(json.loads(res.content))
        else: logging.error("%s - %s - %s returned code %s" % (self.name, endpoint, data, res.status_code))

    def get(self, endpoint, data={}):
        logging.debug("%s - doing get on %s - %s" % (self.name, endpoint, data)) 
        self.auth = requests.AuthObject(self.username, self.password)
        url = "https://convore.com/api/%s" % endpoint
        res = requests.get(url, data, auth=self.auth)
        if res.status_code == 200:
            logging.debug("%s - got result %s" % (self.name, res.content))
            return LazyDict(json.loads(res.content))
        logging.error("%s - %s - %s returned code %s" % (self.name, endpoint, data, res.status_code))

    def connect(self):
        logging.warn("%s - authing %s" % (self.name, self.username))
        r = self.get('account/verify.json')
        if r: logging.warn("%s - connected" % self.name) ; self.connectok.set()
        else: logging.warn("%s - auth failed - %s" % (self.name, r)) ; raise NotConnected(self.username)

    def outnocb(self, printto, txt, how="msg", event=None, origin=None, html=False, *args, **kwargs):
        if event and not event.chan.data.enable:
            logging.warn("%s - channel %s is not enabled" % (self.name, event.chan.data.id))
            return
        txt = self.normalize(txt)
        logging.warn("%s - out - %s - %s" % (self.name, printto, txt))
        if event and event.msg:
            r = self.post("messages/%s/create.json" % printto, data={"message": txt, "pasted": True})
        else:
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
        try:
            id = self.state["idcache"][channel]
            res = self.post("groups/%s/leave.json" % id, {"group_id": id})
        except: handle_exception() ; return
        if channel in self.state['joinedchannels']: self.state['joinedchannels'].remove(channel) ; self.state.save()
        return res

    def _readloop(self):
        self.connectok.wait(15)
        self.auth = requests.AuthObject(self.username, self.password)
        while not self.stopped:
            time.sleep(1)
            if self.cursor: result = self.get("live.json", {"cursor": self.cursor})
            else: result = self.get("live.json")
            if not result: time.sleep(20) ; continue
            if result.has_key("_id"): self.cursor = result["_id"]
            logging.info("%s - incoming - %s" % (self.name, str(result)))
            if not result: continue
            if not result.messages: continue
            for message in result.messages:
                try:
                    event = ConvoreEvent()
                    event.parse(self, message, result)
                    if event.username == self.username: continue
                    event.bind(self)
                    method = getattr(self, "handle_%s" % event.type)
                    method(event)
                except (TypeError, AttributeError): logging.error("%s - no handler for %s kind" % (self.name, message['kind'])) 
                except: handle_exception()

    def handle_error(self, event):
        logging.error("%s - error - %s" % (self.name, event.error))

    def handle_logout(self, event):
        logging.warn("%s - logout - %s" % (self.name, event.username))

    def handle_login(self, event):
        logging.warn("%s - login - %s" % (self.name, event.username))

    def handle_star(self, event):
        pass
        #logging.warn("%s - star - %s" % (self.name, str(message)))

    def handle_topic(self, event):
        logging.warn("%s - topic - %s" % (self.name, event.dump()))

    def handle_message(self, event):
        self.doevent(event)

    def handle_direct_message(self, event):
        self.doevent(event)
 