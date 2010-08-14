# gozerlib/utils/web.py
#
#

""" web related functions. """

## gozerlib imports

from gozerlib.utils.generic import fromenc, getversion

## gaelib imports

from auth import finduser

## basic imports

import os
import time
import socket

## functions

def mini(response, input={}):
    """ display start html so that bot output can follow. """
    from google.appengine.ext.webapp import template
    inputdict = {'version': getversion()}
    if input:
        inputdict.update(input)
    temp = os.path.join(os.getcwd(), 'templates/mini.html')
    outstr = template.render(temp, inputdict)
    response.out.write(outstr)

def start(response, input={}):
    """ display start html so that bot output can follow. """
    try:
         inputdict['url'] = socket.gethostname()
    except AttributeError:
         if os.environ.get('HTTP_HOST'):
             url = os.environ['HTTP_HOST']
         else:
             url = os.environ['SERVER_NAME']
    print url
    inputdict = {'version': getversion(), 'url': "http://%s:8080" % url}

    if input:
        inputdict.update(input)

    temp = os.path.join(os.getcwd(), 'templates/start.html')

    from google.appengine.ext.webapp import template
    outstr = template.render(temp, inputdict)

    response.out.write(outstr)

def commandbox(response, url="/dispatch/"):
    """ write html data for the exec box. """
    response.out.write("""
          <form action="%s" method="post">
            <div><b>enter command:</b> <input type="commit" name="content"></div>
          </form>
          """ % url)

def execbox(response, url="/exec/"):
    """ write html data for the exec box. """
    response.out.write("""
      <form action="" method="GET">
        <b>enter command:</b><input type="commit" name="input" value="">
        // <input type="button" value="go" onClick="makePOSTRequest(this.form)"
      </form>
          """)

def closer(response):
    """ send closing html .. comes after the bot output. """
    response.out.write('</div><div class="footer">')
    response.out.write('<b>%4f seconds</b></div>' % (time.time() - response.starttime))
    response.out.write('</body></html>')

def loginurl(response):
    """ return google login url. """
    from google.appengine.api import users as gusers
    return gusers.create_login_url("/")

def logouturl(response):
    """ return google login url. """
    from google.appengine.api import users as gusers
    return gusers.create_logout_url("/")
