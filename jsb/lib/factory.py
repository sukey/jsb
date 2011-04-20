# jsb/lib/factory.py
#
#

""" Factory to produce instances of classes. """

## jsb imports

from jsb.lib.errors import NoSuchBotType

## Factory base class

class Factory(object):
     pass

## BotFactory class

class BotFactory(Factory):

    def create(self, type, cfg):
        if 'xmpp' in type:
            try:
                import waveapi
                from jsb.drivers.gae.xmpp.bot import XMPPBot
                bot = XMPPBot(cfg)
            except ImportError:   
                from jsb.drivers.xmpp.bot import SXMPPBot
                bot = SXMPPBot(cfg)
        elif type == 'web':
            from jsb.drivers.gae.web.bot import WebBot
            bot = WebBot(cfg)
        elif type == 'wave': 
            from jsb.drivers.gae.wave.bot import WaveBot
            bot = WaveBot(cfg, domain=cfg.domain)
        elif type == 'irc':
            from jsb.drivers.irc.bot import IRCBot
            bot = IRCBot(cfg)
        elif type == 'console':
            from jsb.drivers.console.bot import ConsoleBot
            bot = ConsoleBot(cfg)
        elif type == 'base':
            from jsb.lib.botbase import BotBase
            bot = BotBase(cfg)
        elif type == 'convore':
            from jsb.drivers.convore.bot import ConvoreBot
            bot = ConvoreBot(cfg)
        else: raise NoSuchBotType('%s bot .. unproper type %s' % (type, cfg.dump()))
        return bot

bot_factory = BotFactory()
