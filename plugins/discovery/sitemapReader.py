'''
sitemapReader.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import core.controllers.outputManager as om

# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
import core.data.kb.knowledgeBase as kb
from core.controllers.coreHelpers.fingerprint_404 import is_404
from core.controllers.w3afException import w3afException, w3afRunOnce
from core.data.parsers.urlParser import url_object


class sitemapReader(baseDiscoveryPlugin):
    '''
    Analyze the sitemap.xml file and find new URLs
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        
        # Internal variables
        self._exec = True

    def discover(self, fuzzableRequest ):
        '''
        Get the sitemap.xml file and parse it.
        
        @parameter fuzzableRequest: A fuzzableRequest instance that contains (among other things) the URL to test.
        '''
        if not self._exec:
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
        else:
            # Only run once
            self._exec = False
            self._new_fuzzable_requests = []
            
            base_url = fuzzableRequest.getURL().baseUrl()
            sitemap_url = base_url.urlJoin( 'sitemap.xml' )
            response = self._urlOpener.GET( sitemap_url, useCache=True )
            
            # Remember that httpResponse objects have a faster "__in__" than
            # the one in strings; so string in response.getBody() is slower than
            # string in response
            if '</urlset>' in response and not is_404( response ):
                om.out.debug('Analyzing sitemap.xml file.')
                
                self._new_fuzzable_requests.extend( self._createFuzzableRequests( response ) )
                
                import xml.dom.minidom
                om.out.debug('Parsing xml file with xml.dom.minidom.')
                try:
                    dom = xml.dom.minidom.parseString( response.getBody() )
                except:
                    raise w3afException('Error while parsing sitemap.xml')
                urlList = dom.getElementsByTagName("loc")
                for url in urlList:
                    try:
                        url = url.childNodes[0].data
                        url = url_object(url)
                    except ValueError, ve:
                        om.out.debug('Sitemap file had an invalid URL: "%s"' % ve)
                    except:
                        om.out.debug('Sitemap file had an invalid format')
                    else:
                        # Send the requests using threads:
                        self._run_async(meth=self._get_and_parse, args=(url,))
            
                # Wait for all threads to finish
                self._join()
        
            return self._new_fuzzable_requests
        
    def _get_and_parse(self, url):
        '''
        GET and URL that was found in the robots.txt file, and parse it.
        
        @parameter url: The URL to GET.
        @return: None, everything is saved to self._new_fuzzable_requests.
        '''
        try:
            http_response = self._urlOpener.GET( url, useCache=True )
        except KeyboardInterrupt, k:
            raise k
        except w3afException, w3:
            msg = 'w3afException while fetching page in discovery.sitemapReader, error: "'
            msg += str(w3) + '"'
            om.out.debug( msg )
        else:
            if not is_404( http_response ):
                fuzz_reqs = self._createFuzzableRequests( http_response )
                self._new_fuzzable_requests.extend( fuzz_reqs )
        
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        ol = optionList()
        return ol
        
    def setOptions( self, OptionList ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        pass

    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return []
    
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin searches for the sitemap.xml file, and parses it.
        
        The sitemap.xml file is used by the site administrator to give the Google crawler more
        information about the site. By parsing this file, the plugin finds new URLs and other
        usefull information.
        '''
