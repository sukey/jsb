# handler_channel.py
#
#

""" channel handler. """

## jsb imports

from jsb.version import getversion

## google imports

import webapp2

## basic imports

import sys
import time
import types
import logging

## greet

logging.warn(getversion('CHANNEL'))

## classes

class ChannelHandler(webapp2.RequestHandler):

    def post(self, url=None):
        logging.warn(dir(self.request))
        logging.warn(self.request.body)
        logging.warn(dir(self.response))
        logging.warn(self.response)
        logging.warn(url)

application = webapp2.WSGIApplication([webapp2.Route(r'<url:.*>', ChannelHandler)], 
                                      debug=True)

def main():
    global application
    application.run()

if __name__ == "__main__":
    main()
