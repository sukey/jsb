# waveplugs/rss.py
#
#

"""
    the rss mantra is of the following:

        1) add a url with rss-add <feedname> <url>
        2) use rss-start <feed> 

"""

## gozerlib imports

from gozerlib.persist import Persist, PlugPersist
from gozerlib.utils.url import geturl2, striphtml, useragent
from gozerlib.utils.exception import handle_exception
from gozerlib.utils.generic import strippedtxt, fromenc, toenc, jsonstring
from gozerlib.utils.rsslist import rsslist
from gozerlib.utils.lazydict import LazyDict
from gozerlib.utils.statdict import StatDict
from gozerlib.utils.timeutils import strtotime
from gozerlib.commands import cmnds
from gozerlib.examples import examples
from gozerlib.utils.dol import Dol
from gozerlib.utils.pdod import Pdod
from gozerlib.utils.pdol import Pdol
from gozerlib.users import users
from gozerlib.utils.id import getrssid
from gozerlib.tasks import taskmanager
from gozerlib.callbacks import callbacks
from gozerlib.fleet import fleet

import gozerlib.contrib.feedparser as feedparser

## google imports

try:
    from google.appengine.api.memcache import get, set, delete
except ImportError:
    def get(*args, **kwargs): return
    def set(*args, **kwargs): return
    def delete(*args, **kwargs): return

## tinyurl import

try:
    from waveplugs.tinyurl import get_tinyurl
except ImportError:
    def get_tinyurl(url):
        return [url, ]

## basic imports

import time
import os
import types
import thread
import socket
import xml
import logging
import datetime

## define

allowedtokens = ['updated', 'link', 'summary', 'tags', 'author', 'content', 'title', 'subtitle']
savelist = []
possiblemarkup = {'separator': 'set this to desired item separator', \
'all-lines': "set this to 1 if you don't want items to be aggregated", \
'tinyurl': "set this to 1 when you want to use tinyurls", 'skipmerge': \
"set this to 1 if you want to skip merge commits", 'reverse-order': 'set \
this to 1 if you want the rss items displayed with oldest item first'}

def txtindicts(result, d):

    """ return lowlevel values in (nested) dicts. """

    for j in d.values():

        if type(j) == types.DictType:
            txtindicts(result, j) 
        else:
            result.append(j)

def checkfordate(data, date):

    """ see if date is in data (list of feed items). """

    if not data:
        return False

    for item in data:

        try:
            d = item['updated']
        except (KeyError, TypeError):
            continue

        if date == d:
            return True

    return False

def find_self_url(links):

    for link in links:

        if link.rel == 'self':
            return link.href

    return None

## exceptions

class RssException(Exception):
    pass

class Rss301(RssException):
    pass

class RssStatus(RssException):
    pass

class RssBozoException(RssException):
    pass

class RssNoSuchItem(RssException):
    pass

## classes

class Rssitem(Persist):

    """ item that contains rss data """


    def __init__(self, name="nonameset", url="", owner="noownerset", itemslist=['title', 'link'], watchchannels=[], \
sleeptime=30*60, running=0):

        if True:
            filebase = 'jsondata' + os.sep + 'plugs' + os.sep + 'waveplugs.rss' + os.sep + name
            Persist.__init__(self, filebase + os.sep + 'rss-core')

            if not self.data:
                 self.data = {}

            self.data = LazyDict(self.data)
            self.data['name'] = self.data.name or str(name)
            self.data['url'] = self.data.url or str(url)
            self.data['owner'] = self.data.owner or str(owner)
            self.data['itemslist'] = self.data.itemslist or list(itemslist) # used to initialize feed
            self.data['watchchannels'] = self.data.watchchannels or list(watchchannels)
            self.data['sleeptime'] = self.data.sleeptime or int(sleeptime)
            self.data['running'] = self.data.running or running
            self.data['result'] = self.data.result or []
            self.lastpeek = Persist(filebase + os.sep + 'rss-lastpeek')
            
    def boot(self, name="", url="", itemslist=[], watchchannels=[], \
sleeptime=30*60, running=0, item={}):

        if True:
            self['name'] = name
            self['url'] = url
            self['itemslist'] = list(itemslist)
            self['watchchannels'] = list(watchchannels)
            self['sleeptime'] = int(sleeptime)
            self['running'] = int(running)
            self['stoprunning'] = 0
            self['botname'] = None

    def ownercheck(self, userhost):

        """ check is userhost is the owner of the feed. """

        try:
            return self.data.owner == userhost
        except KeyError:
            pass

        return False

    def save(self):

        """ save rss data. """

        Persist.save(self)
        self.lastpeek.save()

    def getdata(self):
        url = self.data['url']
        result = get(url, namespace='rss')

        if result == None:
            result = self.fetchdata()
            set(url, result, namespace='rss')
            logging.debug("rss - got result from %s" % url)
        else:
            logging.debug("rss - got result from %s *cached*" % url)

        return result

    def fetchdata(self):

        """ get data of rss feed. """

        url = self.data['url']
        result = feedparser.parse(url, agent=useragent())
        logging.debug("rss - fetch - got result from %s" % url)
        
        if result and result.has_key('bozo_exception'):
            logging.info('rss - %s bozo_exception: %s' % (url, result['bozo_exception']))

        try:
            status = result.status
            logging.info("rss - status is %s" % status)
        except AttributeError:
            status = 200

        if status != 200 and status != 301 and status != 302:
            raise RssStatus(status)

        return result.entries

    def sync(self):

        """ refresh cached data of a feed. """

        if not self.data.running:
            logging.info("rss - %s not enabled .. %s not syncing " % (self.data.name, self.data.url))
            return

        logging.info("rss - syncing %s - %s" % (self.data.name, self.data.url))
        result = self.fetchdata()
        cachedresult = get(self.data.url, namespace='rss')
        got = False


        if cachedresult != result:
            set(self.data.url, result, namespace='rss')
            logging.debug('rss - result - %s' % result)
            self.data['result'] = result
            self.save()
            got = True

        return got

    def check(self, userhost, save=True):

        """ get items for user originating the event since lastpeeked. """

        name = userhost

        try:
            lastpeeked = float(self.lastpeek.data[name])
        except (KeyError, ValueError):
            lastpeeked = 0
            logging.debug("last peek of %s is initialised" % str(name))

        logging.debug("using lastpeeked: %s for user %s" % (time.ctime(lastpeeked), name))
        result = self.data['result']

        logging.debug("got %s rss items for %s" % (len(result), name))
        got = False
        tobereturned = []

        if result:
            r = lastpeeked

            for res in result:
                res = LazyDict(res)
                dt = feedparser._parse_date(res.updated)
                #dtt = datetime.datetime.fromtimestamp(time.mktime(dt))

                if not dt:
                    logging.info("rss - %s feed .. can't determine time out of string %s" % (self.data.name, res.updated))
                    return False

                dtt = time.mktime(dt)


                if res.updated:

                    if dtt > r:
                        tobereturned.append(LazyDict(res))
                        r = dtt
                        self.lastpeek.data[name] = dtt
                        logging.debug('lastpeek of %s set to %s' % (name, time.ctime(self.lastpeek.data[name])))
                        got = True

            if got and save:
                self.lastpeek.save()

        return tobereturned

    def all(self):
        return self.data.result

    def search(self, item, search):
        res = []

        for result in self.all():

            try:
                i = getattr(result, item)
            except AttributeError:
                continue

            if i and search in i:
               res.append(i)

        return res


class Rssdict(PlugPersist):

    """ dict of rss entries """

    def __init__(self, filename, feedname=None):
        self.feeds = {}
        PlugPersist.__init__(self, filename)

        if not self.data:
            self.data = {}
            self.data['names'] = []
            self.data['urls'] = {}
        else:
            if not self.data.has_key('names'):
                self.data['names'] = []
            if not self.data.has_key('urls'):
                self.data['urls'] = {}
            if not feedname:
                pass
                #for name in self.data['names']:
                #    self.feeds[name] = Rssitem(name)
            else:
                self.feeds[feedname] = Rssitem(feedname)

        self.itemslists = Pdol('gozerstore' + os.sep + 'plugs' + os.sep + 'waveplugs.rss' + os.sep + filename + '.itemslists')
        self.markup = Pdod('gozerstore' + os.sep + 'plugs' + os.sep + 'waveplugs.rss' + os.sep + filename + '.markup')
        #self.startwatchers()

    def save(self, namein=None):

        """ save all feeds or provide a feedname to save. """

        PlugPersist.save(self)

        for name, feed in self.feeds.iteritems():

            if namein and name != namein:
                continue

            try:
                feed.save()
            except Exception, ex:
                handle_exception()

        self.itemslists.save()
        self.markup.save()

    def size(self):

        """ return number of rss feeds. """

        return len(self.data['names'])

    def add(self, name, url, owner):

        """ add rss item. """

        logging.info('rss - adding %s - %s - (%s)' % (name, url, owner))

        if name not in self.data['names']:
            self.data['names'].append(name)

        self.feeds[name] = Rssitem(name, url, owner, ['title', 'link'])
        self.data['urls'][url] = name
        self.watch(name)
        self.save(name)

    def delete(self, name):

        """ delete rss item by name. """

        target = self.byname(name)
         
        if target:

            try:
                target.data.running = 0
                target.save()
                del self.feeds[name]
                self.save()
            except:
                pass

    def byname(self, name):

        """ return rss item by name. """

        try:
            return self.feeds[name]
        except KeyError:
            item = Rssitem(name)
            if item.data.url:
                self.feeds[name] = item
                return item

    def cloneurl(self, url, auth):

        """ add feeds from remote url. """


        data = geturl2(url)
        got = []

        for line in data.split('\n'):

            try:
                (name, url) = line.split()
            except ValueError:
                logging.debug("rss - cloneurl - can't split %s line" % line)
                continue

            if self.byname(name):
                logging.debug('rss - cloneurl - already got %s feed' % name)
                continue

            if url.endswith('<br>'):
               url = url[:-4]

            self.add(name, url, auth)
            got.append(name)

        return got

    def getdata(self, name):

        """ get data of rss feed. """

        rssitem = self.byname(name)

        if rssitem == None:
            raise RssNoSuchItem("no %s rss item found" % name)

        return rssitem.getdata()

    def watch(self, name):

        """ start a watcher thread """

        # get basic data
        logging.debug('trying %s rss feed watcher' % name)
        rssitem = self.byname(name)

        if rssitem == None:
            raise RssNoItem()

        if not rssitem.data.running:
            rssitem.data.running = 1
            rssitem.data.stoprunning = 0
            rssitem.save()
 
        logging.info('rss - started %s rss watch' % name)

class Rsswatcher(Rssdict):

    """ rss watchers. """ 

    def checkfeed(self, url, event):

        """ get data of rss feed. """

        result = feedparser.parse(url, agent=useragent())
        logging.debug("rss - fetch - got result from %s" % url)
        
        if result and result.has_key('bozo_exception'):
            event.reply('rss - %s bozo_exception: %s' % (url, result['bozo_exception']))
            return False

        try:
            status = result.status
            event.reply("rss - %s - status is %s" % (url, status))
        except AttributeError:
            status = 200

        if status != 200 and status != 301 and status != 302:
            return False

        return True

    def byurl(self, url):

        try:
            name = self.data['urls'][url]
        except KeyError:
            return

        return self.byname(name)

    def insertdata(self, data):

        """ get data of rss feed. """

        result = feedparser.parse(data)
        url = find_self_url(result.feed.links)
        logging.warn("rss - insert - %s - %s" % (url, data))
        
        try:

            rssitem = self.byurl(url)
             
            if rssitem:
                loopover = rssitem.data.watchchannels
                name = rssitem.data.name
            else:
                logging.warn("rss - can't find %s item" % url)
                return

            logging.debug("loopover in %s peek is: %s" % (rssitem.data.name, loopover))

            for item in loopover:

                try:
                    (botname, channel) = item
                except:
                    logging.info('rss - %s is not in the format (botname,channel)' % str(item))

                bot = fleet.byname(botname)

                if not bot:
                    logging.error("rss - can't find %s bot in fleet" % botname)
                    continue

                res2 = result.entries

                if not res2:
                    logging.info("no updates for %s (%s) feed available" % (rssitem.data.name, channel))
                    continue

                if self.markup.get(jsonstring([name, channel]), 'reverse-order'):
                    res2 = res2[::-1]

                if self.markup.get(jsonstring([name, channel]), 'all-lines'):

                    for i in res2:
                        response = self.makeresponse(name, [i, ], channel)

                        try:
                            bot.say(channel, response)
                        except Exception, ex:
                            handle_exception()

                else:
                    
                    sep =  self.markup.get(jsonstring([name, channel]), 'separator')

                    if sep:
                        response = self.makeresponse(name, res2, channel, sep=sep)
                    else:
                        response = self.makeresponse(name, res2, channel)

                    try:
                        bot.say(channel, response)
                    except Exception, ex:
                        handle_exception()

        except Exception, ex:
            handle_exception(txt=name)

        return True

    def getall(self):

        for name in self.data['names']:
            self.feeds[name] = Rssitem(name)

        return self.feeds
       
    def get(self, name, userhost, save=True):
        return self.byname(name).get(userhost, save)

    def check(self, name, userhost, save=True):
        return self.byname(name).check(userhost, save)

    def sync(self, name):

        """ sync a feed. """

        feed = self.byname(name)

        if feed:
            return feed.sync()

    def ownercheck(self, name, userhost):

        """ check if userhost is the owner of feed. """

        try:
            return self.byname(name).ownercheck(userhost)
        except KeyError:
            pass

        return False

    def changeinterval(self, name, interval):

        """ not implemented yet. """

        pass

    def stopwatchers(self):

        """ stop all watcher threads. """

        for j, z in self.data.iteritems():

            if z.data.running:
                z.data.stoprunning = 1

    def dowatch(self, name, sleeptime=1800):

        """ start a watcher. """

        rssitem = self.byname(name)

        if not rssitem == None:
            logging.info("rss - no %s rss item available" % name)
            return

        while 1:

            try:
                self.watch(name)
            except Exception, ex:
                logging.info('rss - %s feed error: %s' % (name, str(ex)))
                if not rssitem.data.running:
                    break
            else:
                break

    def makeresult(self, name, target, data):

        """ make a result (txt) of a feed depending on its itemlist. """

        res = []

        for j in data:
            tmp = {}

            if not self.itemslists.data[jsonstring([name, target])]:
                return []

            for i in self.itemslists.data[jsonstring([name, target])]:
                try:
                    tmp[i] = unicode(j[i])
                except KeyError:
                    continue

            res.append(tmp)

        return res


    def makeresponse(self, name, res, channel, sep=" .. "):

        """ loop over result to make a response. """

        result = u"[%s] - " % name 

        try:
            itemslist = self.itemslists.data[jsonstring([name, channel])]
        except KeyError:
            rssitem = self.byname(name)

            if rssitem == None:
                return "no %s rss item" % name
            else:
                self.itemslists.data[jsonstring([name, channel])] = list(rssitem.data.itemslist)
                self.itemslists.save()

        for j in res:

            if self.markup.get(jsonstring([name, channel]), 'skipmerge') and 'Merge branch' in j['title']:
                continue

            resultstr = u""

            for i in self.itemslists.data[jsonstring([name, channel])]:
                try:
                    item = getattr(j, i)

                    if not item:
                        continue

                    item = unicode(item)

                    if item.startswith('http://'):

                        if self.markup.get(jsonstring([name, channel]), 'tinyurl'):

                            try:
                                tinyurl = get_tinyurl(item)
                                logging.debug('rss - tinyurl is: %s' % str(tinyurl))

                                if not tinyurl:
                                    resultstr += u"%s - " % item
                                else:
                                    resultstr += u"%s - " % tinyurl[0]

                            except Exception, ex:
                                handle_exception()
                                resultstr += u"%s - " % item
	
                        else:
                            resultstr += u"%s - " % item

                    else:
                        resultstr += u"%s - " % item.strip()

                except (KeyError, AttributeError), ex:
                    logging.info('rss - %s - %s' % (name, str(ex)))
                    continue

            resultstr = resultstr[:-3]

            if resultstr:
                result += u"%s %s " % (resultstr, sep)

        return result[:-(len(sep)+2)]

    def peek(self, name, event=None, *args):

        """ poll a feed. display not yet shown items. """

        rssitem = self.byname(name)
        got = False

        if not rssitem:
            logging.debug("rss - skipping peek of %s" % name)
            return

        try:

            if event:
                if event.poller:
                    loopover = [(event.bot.name, event.channel), ]
                else:
                    loopover = [(event.bot.name, event.userhost), ]
            else:
                loopover = rssitem.data.watchchannels

            logging.debug("loopover in %s peek is: %s" % (rssitem.data.name, loopover))

            for item in loopover:

                if event:
                    (botname, channel) = item
                else:
                    
                    try:
                        (botname, channel) = item
                    except:
                        logging.info('rss - %s is not in the format (botname,channel)' % str(item))

                bot = fleet.byname(botname)

                if not bot:
                    logging.error("rss - can't find %s bot in fleet" % botname)
                    continue

                #res2 = self.get(name, channel, False)
                res2 = self.check(name, channel, False)

                if not res2:
                    logging.info("no updates for %s (%s) feed available" % (rssitem.data.name, channel))
                    continue

                got = True

                if self.markup.get(jsonstring([name, channel]), 'reverse-order'):
                    res2 = res2[::-1]

                if self.markup.get(jsonstring([name, channel]), 'all-lines'):

                    for i in res2:
                        response = self.makeresponse(name, [i, ], channel)

                        if event:
                            if event.poller:
                                event.replyroot(response)
                            else:
                                event.reply(response)                             
                        else:

                            try:
                                bot.say(channel, response)
                            except Exception, ex:
                                handle_exception()

                else:
                    
                    sep =  self.markup.get(jsonstring([name, channel]), 'separator')

                    if sep:
                        response = self.makeresponse(name, res2, channel, sep=sep)
                    else:
                        response = self.makeresponse(name, res2, channel)

                    if event:
                        if event.poller:
                            event.replyroot(response)
                        else:
                            event.reply(response)                             
                    else:

                        try:
                            bot.say(channel, response)
                        except Exception, ex:
                            handle_exception()

            if got:
               rssitem.lastpeek.save()

        except Exception, ex:
            handle_exception(txt=name)

        return True

    def stopwatch(self, name):

        """ stop watcher thread. """

        try:
            feed = self.byname(name)
            feed.data.running = 0
            feed.save()
            return True

        except KeyError:
            return False

    def list(self):

        """ return of rss names. """

        feeds = self.data['names']
        return feeds

    def runners(self):	

        """ show names/channels of running watchers. """

        result = []

        for name in self.data['names']:
            z = self.byname(name)
            if z.data.running == 1 and not z.data.stoprunning: 
                result.append((z.data.name, z.data.watchchannels))

        return result

    def getfeeds(self, botname, channel):

        """ show names/channels of running watcher. """

        result = []

        for name in self.data['names']:
            z = self.byname(name)

            if not z.data.running:
                continue

            if jsonstring([botname, channel]) in z.data.watchchannels or [botname, channel] in z.data.watchchannels:
                result.append(z.data.name)

        return result

    def url(self, name):

        """ return url of rssitem. """

        return self.byname(name).data.url

    def seturl(self, name, url):

        """ set url of rssitem. """

        feed = self.byname(name)

        feed.data.url = url
        feed.save()
        return True

    def scan(self, name):

        """ scan a rss url for tokens. """

        try:
            result = self.getdata(name)
        except RssException, ex:
            logging.info('rss - %s error: %s' % (name, str(ex)))
            return

        if not result:
            return

        keys = []

        items = self.byname(name).fetchdata()

        for item in items:
            for key in item:
                if key in allowedtokens:
                    keys.append(key)            

        statdict = StatDict()

        for key in keys:
            statdict.upitem(key)

        return statdict.top()  

    def search(self, name, item, search):

        """ search titles of a feeds cached data. """

        return self.byname(name).search(item, search)


    def searchall(self, item, search):

        """ search titles of all cached data. """

        res = []

        for name in self.data['names']:
            feed = self.byname(name)
            res.append(str(feed.search(item, search)))

        return res

    def all(self, name, item):

        """ search all cached data of a feed. """

        res = []

        for result in self.byname(name).all():

            try:
                txt = getattr(result, item)
            except AttributeError:
                continue

            if txt:
                res.append(txt)

        return res

    def peekall(self, event=None):

        """ peek all feeds. """

        for name in self.data['names']:
            z = self.byname(name)

            if z.data.running:
                #delete(z.data.url)
                self.peek(z.data.name, event)

    def periodical(self, *args, **kwargs):

        """ run periodical .. refresh items. """

        for feed in self.data['names']:
            logging.debug('deleting %s cache entry' % feed)
            dosync(feed)


    def startwatchers(self):

        """ start watcher threads """

        for name in self.data['names']:
            z = self.byname(name)
            if z.data.running:
                self.watch(z.data.name)

    def start(self, botname, name, channel):
        rssitem = self.byname(name)

        if rssitem == None:
            logging.info("we don't have a %s rss object" % name)
            return False

        target = channel

        if not jsonstring([botname, target]) in rssitem.data.watchchannels and not [botname, target] in rssitem.data.watchchannels:
            rssitem.data.watchchannels.append([botname, target])

        rssitem.lastpeek.data[target] = time.time()
        watcher.itemslists[jsonstring([name, target])] = ['title', 'link']
        watcher.markup.set(jsonstring([name, target]), 'tinyurl', 1)
        rssitem.data.running = 1
        rssitem.data.stoprunning = 0
        watcher.save(name)
        watcher.watch(name)
        logging.debug("started %s feed in %s channel" % (name, channel))
        return True

    def stop(self, botname, name, channel):
        rssitem = self.byname(name)

        if not rssitem:
            return False

        try:
            rssitem.data.watchchannels.remove([botname, channel])
            rssitem.save()
            logging.debug("stopped %s feed in %s channel" % (name, channel))
        except ValueError:
            return False

        return True

    def clone(self, botname, newchannel, oldchannel):

        feeds = self.getfeeds(botname, oldchannel)

        for feed in feeds:
            self.stop(botname, feed, oldchannel)
            self.start(botname, feed, newchannel)

        return feeds

# the watcher object 
watcher = Rsswatcher('rss')

assert(watcher)

def dosync(feedname):

    """ main level function to be deferred by periodical. """

    try:
       localwatcher = Rsswatcher('rss', feedname)

       if localwatcher.sync(feedname):
           localwatcher.peek(feedname)

    except RssException, ex:
       logging.info("rss - %s - error: %s" % (feedname, str(ex)))

def doperiodical(*args, **kwargs):

    """ rss periodical function. """
    from google.appengine.ext.deferred import defer

    for feed in watcher.data['names']:
        time.sleep(0.2)
        try:
            defer(dosync, feed)
        except Exception, ex:
            handle_exception()

taskmanager.add('periodical', doperiodical)

def pollerpeek(bot, event):

    """ peek on poll event. """

    feeds = watcher.getfeeds(bot.name, event.channel)
    logging.debug('rss - poller - %s' % str(feeds))

    for feed in feeds:
        watcher.peek(feed, event)

#callbacks.add('POLLER', pollerpeek)


def size():

    """ return number of watched rss entries. """

    return watcher.size()

def save():

    """ save watcher data. """

    watcher.save()

def handle_rssclone(bot, event):
    """ clone feed running in a channel. """
    if not event.rest:
        event.missing('<channel>')
        event.done

    feeds = watcher.clone(bot.name, event.channel, event.rest)
    event.reply('cloned the following feeds: ', feeds)
    bot.say(event.rest, "this wave is continued in %s" % event.url)
 
cmnds.add('rss-clone', handle_rssclone, 'USER')
examples.add('rss-clone', 'clone feeds into new channel', 'wave-clone waveid')

def handle_rsscloneurl(bot, event):

    if not event.rest:
        event.missing('<url>')
        event.done

    feeds = watcher.cloneurl(event.rest, event.auth)
    event.reply('cloned the following feeds: ', feeds)
 
cmnds.add('rss-cloneurl', handle_rsscloneurl, 'OPER')
examples.add('rss-cloneurl', 'clone feeds from remote url', 'wave-clone http://gozerbot.org/feeds')

def handle_rssadd(bot, ievent):

    """ rss-add <name> <url> .. add a rss item. """

    try:
        (name, url) = ievent.args
    except ValueError:
        ievent.missing('<name> <url>')
        return

    if watcher.byname(name):
        ievent.reply('we already have a feed with %s name .. plz choose a different name' % name)
        return

    if watcher.checkfeed(url, ievent):
        watcher.add(name, url, ievent.userhost)
        ievent.reply('rss item added')
    else:
        ievent.reply('%s is not valid' % url)

cmnds.add('rss-add', handle_rssadd, 'USER')
examples.add('rss-add', 'rss-add <name> <url> to the rsswatcher', 'rss-add \
gozerbot http://core.gozerbot.org/hg/dev/0.9/rss-log')

def handle_rssdel(bot, ievent):

    """ rss-del <name> .. delete a rss item. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    rssitem =  watcher.byname(name)

    if rssitem:

        if not watcher.ownercheck(name, ievent.userhost):
            ievent.reply("you are not the owner of the %s feed" % name)
            return

        watcher.stopwatch(name)
        watcher.delete(name)
        ievent.reply('rss item deleted')

    else:
        ievent.reply('there is no %s rss item' % name)

cmnds.add('rss-del', handle_rssdel, ['USER', ])
examples.add('rss-del', 'rss-del <name> .. remove <name> from the rsswatcher', 'rss-del mekker')

def handle_rsssync(bot, ievent):

    """ rss-del <name> .. delete a rss item. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    if name in watcher.data['names']:
        watcher.byname(name).sync()
        ievent.done()
    else:
        ievent.reply("no %s feed available" % name)

cmnds.add('rss-sync', handle_rsssync, ['USER', ])
examples.add('rss-sync', 'rss-sync <name> .. sync <name> feed', 'rss-sync mekker')

def handle_rsswatch(bot, ievent):

    """ rss-watch <name> .. start watcher thread. """

    if not ievent.channel:
        ievent.reply('no channel provided')

    try:
        name, sleepsec = ievent.args
    except ValueError:

        try:
            name = ievent.args[0]
            sleepsec = 1800
        except IndexError:
            ievent.missing('<name> [secondstosleep]')
            return

    try:
        sleepsec = int(sleepsec)
    except ValueError:
        ievent.reply("time to sleep needs to be in seconds")
        return

    rssitem = watcher.byname(name)

    if rssitem == None:
        ievent.reply("we don't have a %s rss object" % name)
        return

    got = None

    if not rssitem.data.running or rssitem.data.stoprunning:

        if not rssitem.data.sleeptime:
            rssitem.data.sleeptime = sleepsec

        rssitem.data.running = 1
        rssitem.data.stoprunning = 0
        got = True
        watcher.save(name)

        try:
            watcher.watch(name)
        except Exception, ex:
            ievent.reply(str(ex))
            return

    if got:
        ievent.reply('watcher started')
    else:
        ievent.reply('already watching %s' % name)

cmnds.add('rss-watch', handle_rsswatch, 'USER')
examples.add('rss-watch', 'rss-watch <name> [seconds to sleep] .. go \
watching <name>', '1) rss-watch gozerbot 2) rss-watch gozerbot 600')

def handle_rssstart(bot, ievent):

    """ rss-start <name> .. start a rss feed to a user. """

    feeds = ievent.args

    if not feeds:
       ievent.missing('<list of feeds>')
       return

    started = []

    if feeds[0] == 'all':
        feeds = watcher.list()

    for name in feeds:
        watcher.start(bot.name, name, ievent.channel)
        started.append(name)

    ievent.reply('started: ', started)

cmnds.add('rss-start', handle_rssstart, ['RSS', 'USER'])
examples.add('rss-start', 'rss-start <name> .. start a rss feed \
(per user/channel) ', 'rss-start gozerbot')

def handle_rssstop(bot, ievent):

    """ rss-start <name> .. start a rss feed to a user. """

    if not ievent.rest:
       ievent.missing('<feed name>')
       return

    name = ievent.rest
    rssitem = watcher.byname(name)
    target = ievent.channel

    if rssitem == None:
        ievent.reply("we don't have a %s rss feed" % name)
        return

    if not rssitem.data.running:
        ievent.reply('%s watcher is not running' % name)
        return

    try:
        rssitem.data.watchchannels.remove([bot.name, target])
    except ValueError:

        try:
            rssitem.data.watchchannels.remove([bot.name, target])
        except ValueError:
            ievent.reply('we are not monitoring %s on (%s,%s)' % (name, bot.name, target))
            return

    rssitem.save()
    ievent.reply('%s stopped' % name)

cmnds.add('rss-stop', handle_rssstop, ['RSS', 'USER'])
examples.add('rss-stop', 'rss-stop <name> .. stop a rss feed \
(per user/channel) ', 'rss-stop gozerbot')

def handle_rssstopall(bot, ievent):

    """ rss-stop <name> .. stop all rss feeds to a channel. """

    if not ievent.rest:
       target = ievent.channel
    else:
       target = ievent.rest
    stopped = []

    feeds = watcher.getfeeds(bot.name, target)

    if feeds:

        for feed in feeds:

            if watcher.stop(bot.name, feed, target):
                stopped.append(feed)

        ievent.reply('stopped feeds: ', stopped)

    else:
        ievent.reply('no feeds running in %s' % target)

cmnds.add('rss-stopall', handle_rssstopall, ['RSS', 'OPER'])
examples.add('rss-stopall', 'rss-stopall .. stop all rss feeds (per user/channel) ', 'rss-stopall')

def handle_rsschannels(bot, ievent):

    """ rss-channels <name> .. show channels of rss feed. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing("<name>") 
        return

    rssitem = watcher.byname(name)

    if rssitem == None:
        ievent.reply("we don't have a %s rss object" % name)
        return

    if not rssitem.data.watchchannels:
        ievent.reply('%s is not in watch mode' % name)
        return

    result = []

    for i in rssitem.data.watchchannels:
        result.append(str(i))

    ievent.reply("channels of %s: " % name, result, dot=True)

cmnds.add('rss-channels', handle_rsschannels, ['OPER', ])
examples.add('rss-channels', 'rss-channels <name> .. show channels', 'rss-channels gozerbot')

def handle_rssaddchannel(bot, ievent):

    """ 
        rss-addchannel <name> [<botname>] <channel> .. add a channel to \
        rss item.
    """

    try:
        (name, botname, channel) = ievent.args
    except ValueError:

        try:
            (name, channel) = ievent.args
            botname = bot.name
        except ValueError:

            try:
                name = ievent.args[0]
                botname = bot.name
                channel = ievent.channel
            except IndexError:
                ievent.missing('<name> [<botname>] <channel>')
                return

    rssitem = watcher.byname(name)

    if rssitem == None:
        ievent.reply("we don't have a %s rss object" % name)
        return

    if not rssitem.data.running:
        ievent.reply('%s watcher is not running' % name)
        return

    if jsonstring([botname, channel]) in rssitem.data.watchchannels or [botname, channel] in rssitem.data.watchchannels:
        ievent.reply('we are already monitoring %s on (%s,%s)' % \
(name, botname, channel))
        return

    rssitem.data.watchchannels.append([botname, channel])
    rssitem.save()
    ievent.reply('%s added to %s rss item' % (channel, name))

cmnds.add('rss-addchannel', handle_rssaddchannel, ['OPER', ])
examples.add('rss-addchannel', 'rss-addchannel <name> [<botname>] <channel> \
..add <channel> or <botname> <channel> to watchchannels of <name>', \
'1) rss-addchannel gozerbot #dunkbots 2) rss-addchannel gozerbot main \
#dunkbots')

def handle_rsssetitems(bot, ievent):

    """ set items of a rss feed. """

    try:
        (name, items) = ievent.args[0], ievent.args[1:]
    except ValueError:
        ievent.missing('<name> <items>')
        return

    target = ievent.channel

    if not watcher.byname(name):
        ievent.reply("we don't have a %s feed" % name)
        return

    watcher.itemslists.data[jsonstring([name, target])] = items
    watcher.itemslists.save()
    ievent.reply('%s added to (%s,%s) itemslist' % (items, name, target))

cmnds.add('rss-setitems', handle_rsssetitems, ['RSS', 'USER'])
examples.add('rss-setitems', 'set tokens of the itemslist (per user/channel)',\
 'rss-setitems gozerbot author author link pubDate')

def handle_rssadditem(bot, ievent):

    """ add an item (token) to a feeds itemslist. """

    try:
        (name, item) = ievent.args
    except ValueError:
        ievent.missing('<name> <item>')
        return

    target = ievent.channel

    feed = watcher.byname(name)

    if not feed:
        ievent.reply("we don't have a %s feed" % name)
        return

    try:
        watcher.itemslists.data[jsonstring([name, target])].append(item)
    except KeyError:
        watcher.itemslists.data[jsonstring([name, target])] = feed.data.itemslist

    watcher.itemslists.save()
    ievent.reply('%s added to (%s,%s) itemslist' % (item, name, target))

cmnds.add('rss-additem', handle_rssadditem, ['RSS', 'USER'])
examples.add('rss-additem', 'add a token to the itemslist (per user/channel)',\
 'rss-additem gozerbot link')

def handle_rssdelitem(bot, ievent):

    """ delete item from a feeds itemlist. """

    try:
        (name, item) = ievent.args
    except ValueError:
        ievent.missing('<name> <item>')
        return

    target = ievent.channel

    if not watcher.byname(name):
        ievent.reply("we don't have a %s feed" % name)
        return

    try:
        watcher.itemslists.data[jsonstring([name, target])].remove(item)
        watcher.itemslists.save()
    except (RssNoSuchItem, ValueError):
        ievent.reply("we don't have a %s rss feed" % name)
        return

    ievent.reply('%s removed from (%s,%s) itemslist' % (item, name, target))

cmnds.add('rss-delitem', handle_rssdelitem, ['RSS', 'USER'])
examples.add('rss-delitem', 'remove a token from the itemslist \
(per user/channel)', 'rss-delitem gozerbot link')

def handle_rssmarkuplist(bot, ievent):

    """ show possible markups that can be used. """

    ievent.reply('possible markups ==> ' , possiblemarkup, dot=True)

cmnds.add('rss-markuplist', handle_rssmarkuplist, ['USER', ])
examples.add('rss-markuplist', 'show possible markup entries', \
'rss-markuplist')

def handle_rssmarkup(bot, ievent):

    """ show the markup of a feed. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    target = ievent.channel

    try:
        ievent.reply(str(watcher.markup[jsonstring([name, target])]))
    except KeyError:
        pass

cmnds.add('rss-markup', handle_rssmarkup, ['RSS', 'USER'])
examples.add('rss-markup', 'show markup list for a feed (per user/channel)', \
'rss-markup gozerbot')

def handle_rssaddmarkup(bot, ievent):

    """ add a markup to a feeds markuplist. """

    try:
        (name, item, value) = ievent.args
    except ValueError:
        ievent.missing('<name> <item> <value>')
        return

    target = ievent.channel

    try:
        value = int(value)
    except ValueError:
        pass

    try:
        watcher.markup.set(jsonstring([name, target]), item, value)
        watcher.markup.save()
        ievent.reply('%s added to (%s,%s) markuplist' % (item, name, target))
    except KeyError:
        ievent.reply("no (%s,%s) feed available" % (name, target))

cmnds.add('rss-addmarkup', handle_rssaddmarkup, ['RSS', 'USER'])
examples.add('rss-addmarkup', 'add a markup option to the markuplist \
(per user/channel)', 'rss-addmarkup gozerbot all-lines 1')

def handle_rssdelmarkup(bot, ievent):

    """ delete markup from a feeds markuplist. """

    try:
        (name, item) = ievent.args
    except ValueError:
        ievent.missing('<name> <item>')
        return

    target = ievent.channel

    try:
        del watcher.markup[jsonstring([name, target])][item]
    except (KeyError, TypeError):
        ievent.reply("can't remove %s from %s feed's markup" %  (item, name))
        return

    watcher.markup.save()
    ievent.reply('%s removed from (%s,%s) markuplist' % (item, name, target))

cmnds.add('rss-delmarkup', handle_rssdelmarkup, ['RSS', 'USER'])
examples.add('rss-delmarkup', 'remove a markup option from the markuplist \
(per user/channel)', 'rss-delmarkup gozerbot all-lines')

def handle_rssdelchannel(bot, ievent):

    """ 
        rss-delchannel <name> [<botname>] <channel> .. delete channel \
        from rss item.

    """

    botname = None

    try:
        (name, botname, channel) = ievent.args
    except ValueError:

        try:
            (name, channel) = ievent.args
            botname = bot.name
        except ValueError:

            try:
                name = ievent.args[0]
                botname = bot.name
                channel = ievent.channel
            except IndexError:
                ievent.missing('<name> [<botname>] [<channel>]')
                return

    rssitem = watcher.byname(name)

    if rssitem == None:
        ievent.reply("we don't have a %s rss object" % name)
        return

    if jsonstring([botname, channel]) in rssitem.data.watchchannels:
        rssitem.data.watchchannels.remove(jsonstring([botname, channel]))
        ievent.reply('%s removed from %s rss item' % (channel, name))
    elif [botname, channel] in rssitem.data.watchchannels:
        rssitem.data.watchchannels.remove([botname, channel])
        ievent.reply('%s removed from %s rss item' % (channel, name))
    else:
        ievent.reply('we are not monitoring %s on (%s,%s)' % (name, botname, \
channel))
        return

    rssitem.save()

cmnds.add('rss-delchannel', handle_rssdelchannel, ['OPER', ])
examples.add('rss-delchannel', 'rss-delchannel <name> [<botname>] \
[<channel>] .. delete <channel> or <botname> <channel> from watchchannels of \
<name>', '1) rss-delchannel gozerbot #dunkbots 2) rss-delchannel gozerbot \
main #dunkbots')

def handle_rssstopwatch(bot, ievent):

    """ rss-stopwatch <name> .. stop a watcher thread. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    rssitem = watcher.byname(name)

    if not rssitem:
        ievent.reply("there is no %s rssitem" % name)
        return

    if not watcher.stopwatch(name):
        ievent.reply("can't stop %s watcher" % name)
        return

    ievent.reply('stopped %s rss watch' % name)

cmnds.add('rss-stopwatch', handle_rssstopwatch, ['OPER', ])
examples.add('rss-stopwatch', 'rss-stopwatch <name> .. stop polling <name>', \
'rss-stopwatch gozerbot')

def handle_rsssleeptime(bot, ievent):

    """ rss-sleeptime <name> .. get sleeptime of rss item. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return
    if not watcher.ownercheck(name, ievent.userhost):
        ievent.reply("you are not the owner of the %s feed" % name)
        return

    rssitem = watcher.byname(name)

    if rssitem == None:
        ievent.reply("we don't have a %s rss item" % name)
        return

    try:
        ievent.reply('sleeptime for %s is %s seconds' % (name, \
str(rssitem.data.sleeptime)))
    except AttributeError:
        ievent.reply("can't get sleeptime for %s" % name)

cmnds.add('rss-sleeptime', handle_rsssleeptime, 'USER')
examples.add('rss-sleeptime', 'rss-sleeptime <name> .. get sleeping time \
for <name>', 'rss-sleeptime gozerbot')

def handle_rsssetsleeptime(bot, ievent):

    """ rss-setsleeptime <name> <seconds> .. set sleeptime of rss item. """

    try:
        (name, sec) = ievent.args
        sec = int(sec)
    except ValueError:
        ievent.missing('<name> <seconds>')
        return

    if not watcher.ownercheck(name, ievent.userhost):
        ievent.reply("you are not the owner of the %s feed" % name)
        return

    if sec < 60:
        ievent.reply('min is 60 seconds')
        return

    rssitem = watcher.byname(name)

    if rssitem == None:
        ievent.reply("we don't have a %s rss item" % name)
        return

    rssitem.data.sleeptime = sec

    if rssitem.data.running:

        try:
            watcher.changeinterval(name, sec)
        except KeyError, ex:
            ievent.reply("failed to set interval: %s" % str(ex))
            return

    watcher.save()
    ievent.reply('sleeptime set')

cmnds.add('rss-setsleeptime', handle_rsssetsleeptime, ['USER', ])
examples.add('rss-setsleeptime', 'rss-setsleeptime <name> <seconds> .. set \
sleeping time for <name> .. min 60 sec', 'rss-setsleeptime gozerbot 600')

def handle_rssget(bot, ievent):

    """ rss-get  <name> .. fetch rss data. """
 
    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    channel = ievent.channel
    rssitem = watcher.byname(name)

    if rssitem == None:
        ievent.reply("we don't have a %s rss item" % name)
        return

    try:
        result = watcher.getdata(name)
    except Exception, ex:
        ievent.reply('%s error: %s' % (name, str(ex)))
        return

    if watcher.markup.get(jsonstring([name, channel]), 'reverse-order'):
        result = result[::-1]

    response = watcher.makeresponse(name, result, ievent.channel)

    if response:
        ievent.reply("results of %s: %s" % (name, response))
    else:
        ievent.reply("can't make a reponse out of %s" % name)

cmnds.add('rss-get', handle_rssget, ['RSS', 'USER'], threaded=True)
examples.add('rss-get', 'rss-get <name> .. get data from <name>', 'rss-get gozerbot')

def handle_rssrunning(bot, ievent):

    """ rss-running .. show which watchers are running. """

    result = watcher.runners()
    resultlist = []
    teller = 1

    for i in result:
        resultlist.append("%s %s" % (i[0], i[1]))

    if resultlist:
        ievent.reply("running rss watchers: ", resultlist, nr=1)
    else:
        ievent.reply('nothing running yet')

cmnds.add('rss-running', handle_rssrunning, ['RSS', 'USER'])
examples.add('rss-running', 'rss-running .. get running rsswatchers', \
'rss-running')

def handle_rsslist(bot, ievent):

    """ rss-list .. return list of rss items. """

    result = watcher.list()
    result.sort()

    if result:
        ievent.reply("rss items: ", result, dot=True)
    else:
        ievent.reply('no rss items yet')

cmnds.add('rss-list', handle_rsslist, ['RSS', 'USER'])
examples.add('rss-list', 'get list of rss items', 'rss-list')

def handle_rssurl(bot, ievent):

    """ rss-url <name> .. return url of rss item. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    if not watcher.ownercheck(name, ievent.userhost):
        ievent.reply("you are not the owner of the %s feed" % name)
        return

    result = watcher.url(name)

    if not result:
        ievent.reply("can't fetch url for %s" % name)
        return

    try:
        if ':' in result.split('/')[1]:
            if not ievent.msg:
                ievent.reply('run this command in a private message')
                return
    except (TypeError, ValueError, IndexError):
        pass

    ievent.reply('url of %s: %s' % (name, result))

cmnds.add('rss-url', handle_rssurl, ['OPER', ])
examples.add('rss-url', 'rss-url <name> .. get url from rssitem with <name>', 'rss-url gozerbot')

def handle_rssseturl(bot, ievent):

    """ rss-seturl <name> <url> .. set url of rss item. """

    try:
        name = ievent.args[0]
        url = ievent.args[1]
    except IndexError:
        ievent.missing('<name> <url>')
        return

    if not watcher.ownercheck(name, ievent.userhost):
        ievent.reply("you are not the owner of the %s feed" % name)
        return

    oldurl = watcher.url(name)

    if not oldurl:
        ievent.reply("no %s rss item found" % name)
        return

    if watcher.seturl(name, url):
        watcher.sync(name)
        ievent.reply('url of %s changed' % name)
    else:
        ievent.reply('failed to set url of %s to %s' % (name, url))

cmnds.add('rss-seturl', handle_rssseturl, ['USER', ])
examples.add('rss-seturl', 'rss-seturl <name> <url> .. change url of rssitem',\
'rss-seturl gozerbot http://core.gozerbot.org/hg/dev/0.9/rss-log')

def handle_rssitemslist(bot, ievent):

    """ rss-itemslist <name> .. show itemslist of rss item. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    try:
        itemslist = watcher.itemslists[jsonstring([name, ievent.channel])]
    except KeyError:
        ievent.reply("no itemslist set for (%s, %s)" % (name, ievent.channel))
        return

    ievent.reply("itemslist of (%s, %s): " % (name, ievent.channel), itemslist)

cmnds.add('rss-itemslist', handle_rssitemslist, ['RSS', 'USER'])
examples.add('rss-itemslist', 'rss-itemslist <name> .. get itemslist of \
<name> ', 'rss-itemslist gozerbot')

def handle_rssscan(bot, ievent):

    """ rss-scan <name> .. scan rss item for used xml items. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    if not watcher.byname(name):
        ievent.reply('no %s feeds available' % name)
        return

    try:
        result = watcher.scan(name)
    except Exception, ex:
        ievent.reply(str(ex))
        return

    if result == None:
        ievent.reply("can't get data for %s" % name)
        return

    res = []

    for i in result:
        res.append("%s=%s" % i)

    ievent.reply("tokens of %s: " % name, res)

cmnds.add('rss-scan', handle_rssscan, ['USER', ])
examples.add('rss-scan', 'rss-scan <name> .. get possible items of <name> ', 'rss-scan gozerbot')

def handle_rsssync(bot, ievent):

    """ rss-sync <name> .. sync rss item data. """

    try:
        name = ievent.args[0]
    except IndexError:
        ievent.missing('<name>')
        return

    #if not watcher.ownercheck(name, ievent.userhost):
    #    ievent.reply("you are not the owner of the %s feed" % name)
    #    return

    result = watcher.sync(name)
    ievent.reply('%s synced' % name)

cmnds.add('rss-sync', handle_rsssync, ['USER', ])
examples.add('rss-sync', 'rss-sync <name> .. sync data of <name>', \
'rss-sync gozerbot')

def handle_rssfeeds(bot, ievent):

    """ rss-feeds <channel> .. show what feeds are running in a channel. """

    try:
        channel = ievent.args[0]
    except IndexError:
        channel = ievent.channel

    try:
        result = watcher.getfeeds(bot.name, channel)

        if result:
            ievent.reply("feeds running in %s: " % channel, result, dot=True)
        else:
            ievent.reply('%s has no feeds running' % channel)

    except Exception, ex:
        ievent.reply("ERROR: %s" % str(ex))

cmnds.add('rss-feeds', handle_rssfeeds, ['USER', 'RSS'])
examples.add('rss-feeds', 'rss-feeds <name> .. show what feeds are running \
in a channel', '1) rss-feeds 2) rss-feeds #dunkbots')

def handle_rsslink(bot, ievent):

    """ search link entries in cached data. """

    try:
        feed, rest = ievent.rest.split(' ', 1)
    except ValueError:
        ievent.missing('<feed> <words to search>')
        return

    rest = rest.strip().lower()

    try:
        res = watcher.search(feed, 'link', rest)

        if not res:
            res = watcher.search(feed, 'feedburner:origLink', rest)

        if res:
            ievent.reply("link: ", res, dot=" \002||\002 ")

    except KeyError:
        ievent.reply('no %s feed data available' % feed)
        return

cmnds.add('rss-link', handle_rsslink, ['RSS', 'USER'])
examples.add('rss-link', 'give link of item which title matches search key', \
'rss-link gozerbot gozer')

def handle_rssdescription(bot, ievent):

    """ search descriptions in cached data. """

    try:
        feed, rest = ievent.rest.split(' ', 1)
    except ValueError:
        ievent.missing('<feed> <words to search>')
        return

    rest = rest.strip().lower()
    res = ""

    try:
        ievent.reply("results: ", watcher.search(feed, 'summary', rest))
    except KeyError:
        ievent.reply('no %s feed data available' % feed)
        return

cmnds.add('rss-description', handle_rssdescription, ['RSS', 'USER'])
examples.add('rss-description', 'give description of item which title \
matches search key', 'rss-description gozerbot gozer')

def handle_rssall(bot, ievent):

    """ search titles of all cached data. """

    try:
        feed = ievent.args[0]
    except IndexError:
        ievent.missing('<feed>')
        return

    try:
        ievent.reply('results: ', watcher.all(feed, 'title'), dot=" \002||\002 ")
    except KeyError:
        ievent.reply('no %s feed data available' % feed)
        return

cmnds.add('rss-all', handle_rssall, ['RSS', 'USER'])
examples.add('rss-all', "give titles of a feed", 'rss-all gozerbot')

def handle_rsssearch(bot, ievent):

    """ search in titles of cached data. """

    try:
        txt = ievent.args[0]
    except IndexError:
        ievent.missing('<txt>')
        return

    try:        
        ievent.reply("results: ", watcher.searchall('title', txt))
    except KeyError:
        ievent.reply('no %s feed data available' % feed)
        return

cmnds.add('rss-search', handle_rsssearch, ['RSS', 'USER'])
examples.add('rss-search', "search titles of all current feeds", \
'rss-search goz')

def handle_rsspeek(bot, ievent):

    """ run a peek of a feed. """

    if not ievent.rest:
        ievent.missing('<feedname>')
        return

    if not watcher.peek(ievent.rest, ievent):
        ievent.reply("no new entries for feed %s" % ievent.rest)
    else:
        ievent.done()

cmnds.add('rss-peek', handle_rsspeek, ['USER', ])

def handle_rsspeekall(bot, ievent):

    """ peek all feeds. """

    watcher.peekall(ievent.rest, event=ievent)
    ievent.done()

cmnds.add('rss-peekall', handle_rsspeekall, ['OPER', ])
