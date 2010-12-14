# gozerlib/datadir.py
#
#

""" the data directory of the bot. """

## basic imports

import re
import os
import shutil
import logging
import os.path
import getpass

## the global datadir

try: homedir = os.path.abspath(os.path.expanduser("~"))
except: homedir = os.getcwd()

isgae = False

try: getattr(os, "mkdir") ; logging.info("datadir - shell detected") ; datadir = homedir + os.sep + ".jsonbot"
except AttributeError: logging.info("datadir - skipping makedirs") ; datadir = "gozerdata" ; isgae = True

## functions

def makedirs(ddir=None):
    """ make subdirs in datadir. """
    global datadir
    if os.path.exists("/etc/debian_version") and getpass.getuser() == 'jsonbot': ddir = "/var/cache/jsonbot"
    else:
        ddir = ddir or datadir
    datadir = ddir
    logging.warn("datadir - %s" % datadir)
    if isgae: return
    if not os.path.isdir(ddir):
        try: os.mkdir(ddir)
        except: logging.warn("can't make %s dir" % ddir) ; os._exit(1)
    logging.warn("making dirs in %s" % ddir)
    try: os.chmod(ddir, 0700)
    except: pass
    last = datadir.split(os.sep)[-1]
    if not os.path.isdir(ddir):
        try:
            import pkg_resources
            source = pkg_resources.resource_filename('gozerdata', '')
            shutil.copytree(source, ddir)
        except ImportError: 
            try:
                source = "gozerdata"
                shutil.copytree(source, ddir)
            except (OSError, IOError): 
                try:
                    source = "/var/lib/jsonbot/gozerdata"
                    shutil.copytree(source, ddir)
                except: logging.error("datadir - failed to copy gozerdata")
    if not os.path.isdir(ddir + os.sep + 'myplugs'):
        try:
            import pkg_resources
            source = pkg_resources.resource_filename('gozerdata', 'myplugs')
            shutil.copytree(source, ddir + os.sep + 'myplugs')
        except ImportError: 
            try:
                source = "gozerdata" + os.sep + "myplugs"
                shutil.copytree(source, ddir + os.sep + "myplugs")
            except (OSError, IOError): 
                try:
                    source = "/var/lib/jsonbot/gozerdata/myplugs"
                    shutil.copytree(source, ddir + os.sep + "myplugs")
                except: logging.error("datadir - failed to copy gozerdata/myplugs")
    if not os.path.isdir(ddir + os.sep + 'examples'):
        try:
            import pkg_resources
            source = pkg_resources.resource_filename('gozerdata', 'examples')
            shutil.copytree(source, ddir + os.sep + 'examples')
        except ImportError: 
            try:
                source = "gozerdata" + os.sep + "examples"
                shutil.copytree(source, ddir + os.sep + "examples")
            except (OSError, IOError): 
                try:
                    source = "/var/lib/jsonbot/gozerdata/examples"
                    shutil.copytree(source, ddir + os.sep + "examples")
                except: logging.error("datadir - failed to copy gozerdata/examples")
    if not os.path.isdir(ddir + os.sep + 'config'):
        os.mkdir(ddir + os.sep + 'config')
        try:
            import pkg_resources
            source = pkg_resources.resource_filename('gozerdata', 'examples')
            shutil.copy(source + os.sep + 'mainconfig.example', ddir + os.sep + 'config' + os.sep + 'mainconfig')
        except (ImportError, IOError): 
            try:
                source = "gozerdata" + os.sep + "examples"
                shutil.copy(source + os.sep + 'mainconfig.example', ddir + os.sep + 'config' + os.sep + 'mainconfig')
            except (OSError, IOError): 
                try:
                    source = "/var/lib/jsonbot/gozerdata/examples"
                    shutil.copy(source + os.sep + 'mainconfig.example', ddir + os.sep + 'config' + os.sep + 'mainconfig')
                except: logging.error("datadir - failed to copy gozerdata/examples/mainconfig.example")
    try:
        import pkg_resources
        source = pkg_resources.resource_filename('commonplugs', '')
        shutil.copyfile(source + os.sep + "__init__.py", ddir + os.sep + '__init__.py')
    except ImportError:
        try:
            source = "commonplugs"
            shutil.copyfile(source + os.sep + "__init__.py", ddir + os.sep + '__init__.py')
        except (OSError, IOError): pass 
    if not os.path.isdir(ddir + os.sep + 'myplugs'): os.mkdir(ddir + os.sep + 'myplugs')
    try:
        import pkg_resources
        source = pkg_resources.resource_filename('commonplugs', '')
        shutil.copyfile(source + os.sep + "__init__.py", os.path.join(ddir,'myplugs', '__init__.py'))
    except ImportError:
        try:
            source = "commonplugs"
            shutil.copyfile(source + os.sep + "__init__.py", os.path.join(ddir,'myplugs', '__init__.py'))
        except (OSError, IOError): pass
    if not os.path.isdir(ddir + os.sep +'botlogs'): os.mkdir(ddir + os.sep + 'botlogs')
    if not os.path.isdir(ddir + '/run/'): os.mkdir(ddir + '/run/')
    if not os.path.isdir(ddir + '/examples/'): os.mkdir(ddir + '/examples/')
    if not os.path.isdir(ddir + '/users/'): os.mkdir(ddir + '/users/')
    if not os.path.isdir(ddir + '/channels/'): os.mkdir(ddir + '/channels/')
    if not os.path.isdir(ddir + '/fleet/'): os.mkdir(ddir + '/fleet/')
    if not os.path.isdir(ddir + '/pgp/'): os.mkdir(ddir + '/pgp/')
    if not os.path.isdir(ddir + '/plugs/'): os.mkdir(ddir + '/plugs/')
    if not os.path.isdir(ddir + '/old/'): os.mkdir(ddir + '/old/')

def getdatadir():
    global datadir
    return datadir
