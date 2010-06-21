'''
Created on 17 Jun 2010

@author: enmarkp
'''
from genshi.builder import tag
from trac.core import Component, ExtensionPoint, implements
from trac.web.api import ITemplateStreamFilter
from api import ISourceBrowserContextMenuProvider
from genshi.filters.transform import Transformer, StreamBuffer
from genshi.core import START, Markup
from trac.config import Option
from trac.web.chrome import add_stylesheet, ITemplateProvider, add_javascript
from pkg_resources import resource_filename
try:
    from svnurls import SVNURLs
except ImportError:
    SVNURLs = None

class SubversionLink(Component):
    """Generate direct link to file in svn repo"""
    implements(ISourceBrowserContextMenuProvider)
    order = 0
    svn_base_url = Option('svn', 'repository_url')
    separator_after = False
    # IContextMenuProvider methods
    def get_content(self, req, entry, stream, data):
        href      = req.href.svn(data['reponame'], entry.path, rev=data['stickyrev'])
        return tag.a('Subversion URL', href=href)


class DeleteResourceLink(Component):
    """Generate "Delete" menu item"""      
    implements(ISourceBrowserContextMenuProvider)
    order = 5
    separator_after = True
    # IContextMenuProvider methods
    def get_content(self, req, entry, stream, data):
        href = req.href.browser(data['reponame'], entry.path, 
                                rev=data['stickyrev'], delete=1)
        return tag.a('Delete...', href=req.href.delete(entry.path) + 'FIXME')

class SendResourceLink(Component):
    """Generate "Share file" menu item"""
    implements(ISourceBrowserContextMenuProvider)
    order = 10
    separator_after = False
    # IContextMenuProvider methods
    def get_content(self, req, entry, stream, data):
        if not entry.isdir:
            return tag.a('Share file...', href=req.href.share(entry.path) + 'FIXME')

class CreateSubFolderLink(Component):
    """Generate "Create subfolder" menu item"""
    implements(ISourceBrowserContextMenuProvider)
    order = 15
    separator_after = False
    # IContextMenuProvider methods
    def get_content(self, req, entry, stream, data):
        if entry.isdir:
            return tag.a('Create subfolder', href=req.href.newfolder(entry.path) + 'FIXME')
    
class SourceBrowserContextMenu(Component):
    
    implements(ITemplateStreamFilter, ITemplateProvider)
    
    context_menu_providers = ExtensionPoint(ISourceBrowserContextMenuProvider)
    
    # ITemplateStreamFilter methods
    
    def filter_stream(self, req, method, filename, stream, data):
        if filename in ('browser.html', 'dir_entries.html'):
            # FIXME: The idx is only good for finding rows, not generating element ids.
            # Xhr rows are only using dir_entries.html, not browser.html.
            # The xhr-added rows' ids are added using js (see expand_dir.js)
            idx = 0
            menu = None
            add_stylesheet(req, 'contextmenu/contextmenu.css')
            add_javascript(req, 'contextmenu/contextmenu.js')
            if 'up' in data['chrome']['links']:
                # Start appending stuff on 2nd tbody row when we have a parent dir link
                row_index = 2
                # Remove colspan and insert an empty cell for checkbox column
                stream |= Transformer('//table[@id="dirlist"]//td[@colspan="5"]').attr('colspan', None).before(tag.td())
            else:
                row_index = 1
            for entry in data['dir']['entries']:
                menu = tag.div(tag.span(Markup('&#9662;')), # FIXME; image instead
                               tag.ul(style="display:none"), id="ctx%s" % idx, 
                               class_="context-menu")
                for provider in sorted(self.context_menu_providers, key=lambda x: x.order):
                    content = provider.get_content(req, entry, stream, data)
                    if content:
                        menu.children[1].append(tag.li(content))
                    if (hasattr(provider, 'separator_after') 
                            and provider.separator_after):
                        menu.children[1].append(tag.li("---")) # FIXME
                if menu:
                    ## XHR rows don't have a tbody in the stream
                    if data['xhr']:
                        path_prefix = ''
                    else:
                        path_prefix = '//table[@id="dirlist"]//tbody'
                    # Add the menu
                    stream |= Transformer('%s//tr[%d]//td[@class="name"]' % (path_prefix, idx + row_index)).prepend(menu)
                    # Add a checkbox
                    cb = tag.td(tag.input(type='checkbox', id="cb%s" % idx, class_='fileselect'))
                    stream |= Transformer('%s//tr[%d]//td[@class="name"]' % (path_prefix, idx + row_index)).before(cb)
                    
                idx += 1
            stream |= Transformer('//th[1]').before(tag.th())   
        return stream
    
    # ITemplateProvider methods
    
    def get_htdocs_dirs(self):
        return [('contextmenu', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []
