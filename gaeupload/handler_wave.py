# handler_wave.py
#
#

""" this handler handles all the wave jsonrpc requests. """

## gozerlib imports

from gozerlib.version import getversion
from gozerlib.errors import NoSuchCommand
from gozerlib.boot import boot

## gaelib imports

from gozerlib.gae.wave.bot import WaveBot

## basic imports

import logging
import os

## defines

logging.info(getversion('GAE WAVE'))
boot()

# the bot

bot = WaveBot(domain="googlewave.com")

def main():
    bot.run()

if __name__ == "__main__":
    main()
