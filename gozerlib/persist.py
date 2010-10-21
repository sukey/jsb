# gozerlib/persist.py
#
#

"""
    allow data to be written to disk or BigTable in JSON format. creating 
    the persisted object restores data. 

"""

## gozerlib imports

from utils.trace import whichmodule, calledfrom
from utils.lazydict import LazyDict
from utils.exception import handle_exception
from utils.name import stripname
from utils.locking import lockdec
from datadir import datadir
from cache import get, set

## simplejson imports

from simplejson import load, dump, loads, dumps

## basic imports

import thread
import logging
import os
import types
import copy
import sys

## try google first

try:
    from google.appengine.ext import db
    import google.appengine.api.memcache as mc
    from google.appengine.api.datastore_errors import Timeout
    logging.debug("persist - using BigTable based Persist")

    ## JSONindb class

    class JSONindb(db.Model):
        """ model to store json files in. """
        modtime = db.DateTimeProperty(auto_now=True, indexed=False)
        createtime = db.DateTimeProperty(auto_now_add=True, indexed=False)
        filename = db.StringProperty()
        content = db.TextProperty(indexed=False)

    ## Persist class

    class Persist(object):

        """ persist data attribute to database backed JSON file. """ 

        def __init__(self, filename, default={}):
            self.plugname = calledfrom(sys._getframe())
            if 'lib' in self.plugname: self.plugname = calledfrom(sys._getframe(1))
            self.fn = unicode(filename.strip()) # filename to save to
            self.logname = os.sep.join(self.fn.split(os.sep)[-2:])
            self.key = None
            self.obj = None
            self.init(default)

        def init(self, default={}, filename=None):
            fn = self.fn.replace("@", "+")
            fn = fn.replace("#", "+")
            cache = ""
            tmp = get(self.fn) or get(fn) ; cache = "mem"
            if tmp: self.data = tmp ; return
            else: jsontxt =  mc.get(self.fn) or mc.get(fn) ; cache = "cache"
            if type(default) == types.DictType:
                default2 = LazyDict()
                default2.update(default)
            else: default2 = copy.deepcopy(default)
            if jsontxt is None:
                logging.debug("persist - %s - loading from db" % self.logname) 
                try:
                    try: self.obj = JSONindb.get_by_key_name(fn)
                    except Timeout: self.obj = JSONindb.get_by_key_name(fn)
                except Exception, ex:
                    # bw compat sucks
                    try: self.obj = JSONindb.get_by_key_name(fn)
                    except Exception, ex:
                        handle_exception()
                        self.data = default2
                        return
                if self.obj == None:
                    logging.debug("persist - %s - no entry found" % self.logname)
                    self.obj = JSONindb(key_name=self.fn)
                    self.obj.content = unicode(default)
                    self.data = default2
                    return
                jsontxt = self.obj.content
                if jsontxt: mc.set(self.fn, jsontxt)
                logging.debug('persist - jsontxt is %s' % jsontxt)
                gotcache = False
            else: gotcache = True
            self.data = loads(jsontxt)
            if type(self.data) == types.DictType:
                d = LazyDict()
                d.update(self.data)
                self.data = d
            cfrom = whichmodule()
            if 'gozerlib' in cfrom: 
                cfrom = whichmodule(2)
                if 'gozerlib' in cfrom: cfrom = whichmodule(3)
            cfrom = whichmodule(2)
            if 'gozerlib' in cfrom: 
                cfrom = whichmodule(3)
                if 'gozerlib' in cfrom: cfrom = whichmodule(4)
            if not 'run' in self.fn: 
                if cache: logging.warn("persist - %s - loaded %s (%s) - %s - %s" % (cache, self.logname, len(jsontxt), self.data.tojson(), cfrom))
                else: logging.warn("persist - db - loaded %s (%s) - %s - %s" % (self.logname, len(jsontxt), self.data.tojson(), cfrom))
            set(self.fn, self.data)

        def sync(self):
            logging.warn("persist - syncing %s" % self.fn)
            data = dumps(self.data)
            set(self.fn, self.data) ; mc.set(self.fn, self.data)
            return data
     
        def save(self):
            """ save json data to database. """
            bla = dumps(self.data)
            if self.obj == None:
                self.obj = JSONindb(key_name=self.fn)
                self.obj.content = bla
            else: self.obj.content = bla
            self.obj.filename = self.fn
            key = self.obj.put()  
            cfrom = whichmodule(0)
            if 'gozerlib' in cfrom: 
                cfrom = whichmodule(2)
                if 'gozerlib' in cfrom: cfrom = whichmodule(3)
            set(self.fn, bla)
            mc.set(self.fn, bla)
            logging.warn('persist - %s - saved %s (%s)' % (cfrom, self.logname, len(bla)))

        def upgrade(self, filename):
            self.init(self.data, filename=filename)


except ImportError:

    ## file based persist

    logging.debug("using file based Persist")

    ## defines

    persistlock = thread.allocate_lock()
    persistlocked = lockdec(persistlock)

    ## imports for shell bots

    from gozerlib.cache import get, set
    import fcntl

    ## classes

    class Persist(object):

        """ persist data attribute to JSON file. """

        
        def __init__(self, filename, default=None, init=True):
            """ Persist constructor """
            self.fn = filename.strip() # filename to save to
            self.logname = os.sep.join(self.fn.split(os.sep)[-2:])
            self.lock = thread.allocate_lock() # lock used when saving)
            self.data = LazyDict() # attribute to hold the data
            if init:
                if default == None: default = LazyDict()
                self.init(default)

        def init(self, default={}, filename=None):
            """ initialize the data. """
            logging.debug('persist - reading %s' % self.fn)
            gotcache = False
            fn = self.fn.replace("@", "+")
            fn = fn.replace("#", "+")
            try:
                data = get(self.fn)
                if not data: data = get(fn)
                if not data:
                   if os.path.exists(fn): datafile = open(fn, 'r')
                   else: datafile = open(self.fn, 'r')
                   data = datafile.read()
                   datafile.close()
                else:
                    if type(data) == types.DictType:
                        d = LazyDict()
                        d.update(data)
                    else: d = data
                    self.data = d
                    return
            except IOError, ex:
                if not 'No such file' in str(ex):
                    logging.error('persist - failed to read %s: %s' % (self.logname, str(ex)))
                    raise
                else:
                    logging.debug("persist - %s doesn't exist yet" % self.logname)
                    return
            try:
                self.data = loads(data)
                set(self.fn, self.data)
                if type(self.data) == types.DictType:
                    d = LazyDict()
                    d.update(self.data)
                    self.data = d
                cfrom = whichmodule(2)
                if 'gozerlib' in cfrom: 
                    cfrom = whichmodule(3)
                    if 'gozerlib' in cfrom: cfrom = whichmodule(4)
                if not 'run' in self.fn: 
                    size = len(data)
                    if gotcache: logging.info("persist - cache - loaded %s (%s) - %s - %s" % (self.logname, size, self.data.tojson(), cfrom))
                    else: logging.info("persist - file - loaded %s (%s) - %s - %s" % (self.logname, size, self.data.tojson(), cfrom))
            except Exception, ex:
                logging.error('persist - ERROR: %s' % self.fn)
                raise

        def upgrade(self, filename):
            self.init(self.data, filename=filename)
            self.save(filename)

        def get(self):
            return loads(get(self.fn)) 

        def sync(self):
            logging.warn("persist - syncing %s" % self.fn)
            set(self.fn, self.data)
            return self.data

        @persistlocked
        def save(self, filename=None):
            """ persist data attribute. """
            try:
                fn = filename or self.fn
                data = dumps(self.data)
                set(fn, self.data)
                dirr = []
                for p in self.fn.split(os.sep)[:-1]:
                    dirr.append(p)
                    pp = os.sep.join(dirr)
                    if not os.path.isdir(pp):
                        logging.warn("persist - creating %s dir" % pp)
                        os.mkdir(pp)
                tmp = fn + '.tmp' # tmp file to save to
                try: datafile = open(tmp, 'w')
                except IOError, ex:
                    logging.error("persist - can't save %s: %s" % (self.logname, str(ex)))
                    return
                fcntl.flock(datafile, fcntl.LOCK_EX)
                dump(self.data, datafile)
                fcntl.flock(datafile, fcntl.LOCK_UN)
                datafile.close()
                try: os.rename(tmp, fn)
                except OSError:
                    handle_exception()
                    os.remove(self.fn)
                    os.rename(tmp, fn)
                logging.warn('persist - %s saved (%s)' % (self.logname, len(data)))
            except: handle_exception()
            finally: pass

class PlugPersist(Persist):

    """ persist plug related data. data is stored in jsondata/plugs/{plugname}/{filename}. """

    def __init__(self, filename, default=None):
        plugname = calledfrom(sys._getframe())
        Persist.__init__(self, datadir + os.sep + 'plugs' + os.sep + stripname(plugname) + os.sep + stripname(filename))
