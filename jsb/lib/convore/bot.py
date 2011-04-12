# jsb/lib/convore/bot.py
#
#

""" convore bot. """

## jsb import

from jsb.lib.botbase import BotBase
from jsb.imports import getjson, getrequests

## basic imports

import logging

## defines

json = getjson()
requests = getrequests()

## ConvoreBot

class ConvoreBot(BotBase):

    def connect(self):
        logging.warn("%s - authing" % self.name)
        conv_auth = requests.AuthObject(self.user, self.password)
        r = requests.get('https://convore.com/api/account/verify.json', auth=conv_auth)
        if r:
            self.username = json.loads(r.content)['username']
            logging.warn("%s - connected" % self.name)
        else: logging.warn("%s - auth failed - %s - %s" % (self.name, r.status_code, r.content))
 
    def outnocb(self, printto, txt, how="msg", event=None, origin=None, html=False, *args, **kwargs):
        logging.warn("%s - out - %s - %s" % (printto, txt))
        conv_auth = requests.AuthObject(self.username, self.password)
        r = requests.post("https://convore.com/api/topics/%s/messages/create.json" % printto, data={"message": txt}, auth=conv_auth)
        if r.status_code == 200: logging.warn("%s - message posted for %s" % (self.name, self.username))
        else: logging.warn("%s - failed to post message - %s - %s" % (self.name, r.status_code, r.content))
