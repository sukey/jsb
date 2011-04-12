# jsb/lib/convore/bot.py
#
#

""" convore bot. """

## jsb import

from jsb.lib.botbase import BotBase
from jsb.lib.errors import NotConnected
from jsb.lib.convore.event import ConvoreEvent
from jsb.utils.lazydict import LazyDict
from jsb.imports import getjson, getrequests

## basic imports

import logging
import time

## defines

json = getjson()
requests = getrequests()

## API



## ConvoreBot

class ConvoreBot(BotBase):

    """ The Convore Bot. """

    type = "convore"

    def post(self, endpoint, data=None):
        logging.warn("%s - doing post on %s - %s" % (self.name, endpoint, data)) 
        self.auth = requests.AuthObject(self.username, self.password)
        res = requests.post("https://convore.com/api/%s" % endpoint, data or {}, auth=self.auth)
        logging.warn("%s - got result %s" % (self.name, res.content))
        if res.status_code == 200:
            logging.warn("%s - got result %s" % (self.name, res.content))
            return LazyDict(json.loads(res.content))
        else: logging.error("%s - %s - %s returned code %s" % (self.name, endpoint, data, res.status_code))

    def get(self, endpoint, data=None, auth=None):
        logging.warn("%s - doing get on %s - %s" % (self.name, endpoint, data)) 
        self.auth = requests.AuthObject(self.username, self.password)
        res = requests.get("https://convore.com/api/%s" % endpoint, data or {}, auth=self.auth)
        if res.status_code == 200:
            logging.warn("%s - got result %s" % (self.name, res.content))
            return LazyDict(json.loads(res.content))
        logging.error("%s - %s - %s returned code %s" % (self.name, endpoint, data, res.status_code))
      
    def connect(self):
        logging.warn("%s - authing %s" % (self.name, self.username))
        self.auth = requests.AuthObject(self.username, self.password)
        r = self.get('account/verify.json')
        if r:
            logging.warn("%s - connected" % self.name)
            self.connectok.set()
        else:
            logging.warn("%s - auth failed - %s" % (self.name, r))
            raise NotConnected(self.username)

    def outnocb(self, printto, txt, how="msg", event=None, origin=None, html=False, *args, **kwargs):
        logging.warn("%s - out - %s - %s" % (self.name, printto, txt))
        r = self.post("topics/%s/messages/create.json" % printto, data={"message": txt})
        logging.warn("%s - message posted for %s" % (self.name, self.username))

    def discover(self, channel):
        res = self.get("groups/discover/search.json", {"q": channel })
        print res
        return res

    def join(self, channel, password=None):
        if len(channel) < 3: raise Exception("%s channel name is too small" % channel)
        logging.warn("%s - join %s" % (self.name, channel))
        data = self.discover(channel)
        for group in data.groups:
            g = LazyDict(group)
            if g.name != channel: continue
            res = self.post("groups/%s/join.json" % g.id, {"group_id": g.id})
            if res:
                self.say(g.id, "yoooo")
                topics = self.get("groups/%s/topics.json" % g.id)
                print topics
            return res

    def part(self, channel):
        if len(channel) < 3: raise Exception("%s channel name is too small" % channel)
        logging.warn("%s - part %s" % (self.name, channel))
        data = self.discover(channel)
        for group in data.groups:
            g = LazyDict(group)
            if g.name != channel: continue
            res = self.post("groups/%s/leave.json" % g.id, {"group_id": g.id})
            return res

    def _readloop(self):
        self.auth = requests.AuthObject(self.username, self.password)
        self.connectok.wait(10)
        while not self.stopped:
            time.sleep(1)
            result = self.get("live.json")
            if not result: break
            for message in result.messages:
                event = ConvoreEvent(message)
                event.parse(self, message)
                self.doevent(event)
            else: break
