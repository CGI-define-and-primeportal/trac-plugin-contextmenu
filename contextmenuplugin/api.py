'''
Created on 17 Jun 2010

@author: enmarkp
'''
from trac.core import Interface

class ISourceBrowserContextMenuProvider(Interface):
    # Sort order
    order = 0
    # Whether a separator should be rendered after this provider
    separator_after = False
    # Entry point
    def get_content(req, item, stream, data):
        """Return some content the ExtensionPoint is happy with"""
