# coding: utf-8
#
# Copyright (c) 2010, Logica
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither Logica nor the names of its contributors may be used to 
#       endorse or promote products derived from this software without 
#       specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------
'''
Created on 17 Jun 2010

@author: enmarkp
'''
from genshi.builder import tag
from trac.core import Component, ExtensionPoint, implements
from trac.web.api import ITemplateStreamFilter
from api import ISourceBrowserContextMenuProvider
from genshi.core import Markup, START, END, QName, _ensure
from trac.config import Option
from trac.web.chrome import add_stylesheet, ITemplateProvider, add_javascript, add_ctxtnav
from trac.util.compat import all
from trac.util.translation import _
from pkg_resources import resource_filename
import os
import uuid

class InternalNameHolder(Component):
    """ This component holds a reference to the file on this row
    for the javascript to use"""
    implements(ISourceBrowserContextMenuProvider)
    # IContextMenuProvider methods
    def get_order(self, req):
        return 0

    def get_draw_separator(self, req):
        return False
    
    def get_content(self, req, entry, data):
        reponame = data['reponame'] or ''
        filename = os.path.normpath(os.path.join(reponame, entry.path))
        return tag.span(filename, class_="filenameholder %s" % entry.kind,
                        style="display:none")
    
class SubversionLink(Component):
    """Generate direct link to file in svn repo"""
    implements(ISourceBrowserContextMenuProvider)

    svn_base_url = Option('svn', 'repository_url')

    # IContextMenuProvider methods
    def get_order(self, req):
        return 1

    def get_draw_separator(self, req):
        return True
    
    def get_content(self, req, entry, data):
        if self.env.is_component_enabled("svnurls.svnurls.svnurls"):
            # They are already providing links to subversion, so we won't duplicate them.
            return None
        if isinstance(entry, basestring):
            path = entry
        else:
            try:
                path = entry.path
            except AttributeError:
                path = entry['path']
        href = self.svn_base_url.rstrip('/')
        if data['reponame']:
            href += '/' + data['reponame']
        if path != '/':
            href += '/' + path
        return tag.a(_('Subversion URL'), href=href, class_='external svn')

class ContextMenuTransformation(object):
    def __init__(self, req, data, context_menu_providers):
        self.req = req
        self.data = data
        self.context_menu_providers = context_menu_providers

    def __call__(self, stream):
        """Apply the transform filter to the marked stream.

        :param stream: The marked event stream to filter
        """
        found_first_th = False
        if self.data['xhr']:
            in_dirlist = True # XHR rows are only the interesting table
        else:
            in_dirlist = False
        in_repoindex = in_name_td = False
        idx = 0
        rows_seen = 0
        
        if self.data['dir']['entries']:
            has_entries = True 
        else:
            has_entries = False
        
        for kind, data, pos in stream:
            if kind == START:
                if all((data[0] == QName("http://www.w3.org/1999/xhtml}table"),
                        data[1].get('id') in ('dirlist', 'repoindex'),
                        self.data['dir'])):
                    in_dirlist = True
                    in_repoindex = data[1].get('id') == 'repoindex'
                if all((in_dirlist, not found_first_th,
                        data[0] == QName("http://www.w3.org/1999/xhtml}th"))):
                    for event in _ensure(tag.th(Markup('&nbsp;'))):
                        yield event
                    found_first_th = True
                    yield kind, data, pos
                    continue
                if in_dirlist and data[0] == QName("http://www.w3.org/1999/xhtml}td"):
                    rows_seen = rows_seen + 1
                    if 'up' in self.data['chrome']['links'] and rows_seen == 1:
                        data = data[0], data[1] - 'colspan' | [(QName('colspan'), '7')]
                        yield kind, data, pos
                        continue # don't mess with the "parent link" row
                    if 'up' not in self.data['chrome']['links'] and not has_entries:
                        data = data[0], data[1] - 'colspan' | [(QName('colspan'), '7')]
                        yield kind, data, pos
                        continue # don't mess with the "No files found" row
                    if data[1].get('class') == 'name':
                        # would be nice to get this static for any particular
                        # item. We can't use a simple offset count due
                        # to the XHR requests
                        uid = uuid.uuid4()
                        for event in _ensure(tag.td(tag.input(type='checkbox',
                                                              id="cb-%s" % uid,
                                                              class_='fileselect'))):
                            yield event
                        in_name_td = True
            elif in_dirlist and kind == END and data == QName("http://www.w3.org/1999/xhtml}table"):
                # we're leaving the current table; reset markers 
                in_dirlist = False
                rows_seen = 0
                found_first_th = False
                idx = 0
            elif in_name_td and kind == END:
                if data == QName("http://www.w3.org/1999/xhtml}td"):
                    in_name_td = False
                elif data == QName("http://www.w3.org/1999/xhtml}a"):
                    yield kind, data, pos
                    if idx == 0 and in_repoindex:
                        # Don't yield a context menu for the repos since they don't have a dir entry
                        continue
                    menu = tag.div(tag.a(Markup('&nbsp;'), class_="ctx-expander"),
                                   tag.div(class_="ctx-foldable"), tabindex="50",
                                   id="ctx-%s" % uid, class_="context-menu")
                    for provider in sorted(self.context_menu_providers, key=lambda x: x.get_order(self.req)):
                        entry = self.data['dir']['entries'][idx]
                        content = provider.get_content(self.req, entry, self.data)
                        if content:
                            menu.children[1].append(tag.div(content))
                    for event in _ensure(menu):
                        yield event
                    idx = idx + 1
                    continue
            yield kind, data, pos

class SourceBrowserContextMenu(Component):
    """Component for adding a context menu to each item in the trac browser
    file-list
    """
    implements(ITemplateStreamFilter, ITemplateProvider)
    
    context_menu_providers = ExtensionPoint(ISourceBrowserContextMenuProvider)
    
    # ITemplateStreamFilter methods
    
    def filter_stream(self, req, method, filename, stream, data):
        if filename in ('browser.html', 'dir_entries.html'):
            if 'path' not in data:
                # Probably an upstream error
                return stream
            # provide a link to the svn repository at the top of the Browse Source listing
            if self.env.is_component_enabled("contextmenu.contextmenu.SubversionLink"):
                add_ctxtnav(req, SubversionLink(self.env).get_content(req, data['path'], data), category='ctxtnav-list')
            add_stylesheet(req, 'contextmenu/contextmenu.css')
            add_javascript(req, 'contextmenu/contextmenu.js')
            stream |= ContextMenuTransformation(req, data, self.context_menu_providers)
        return stream
    
    # ITemplateProvider methods
    
    def get_htdocs_dirs(self):
        return [('contextmenu', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []
