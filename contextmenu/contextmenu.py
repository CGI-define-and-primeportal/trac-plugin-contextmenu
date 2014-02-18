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
from genshi.filters.transform import Transformer
from trac.core import Component, ExtensionPoint, implements
from trac.web.api import ITemplateStreamFilter
from api import ISourceBrowserContextMenuProvider
from genshi.core import Markup, START, END, QName, _ensure
from trac.config import Option
from trac.web import ITemplateStreamFilter
from trac.web.chrome import (add_stylesheet, ITemplateProvider, add_javascript,
                            add_ctxtnav, add_script, add_script_data)
from trac.web.api import IRequestHandler, IRequestFilter
from trac.util.compat import all
from trac.util.translation import _
from trac.util.presentation import to_json
from pkg_resources import resource_filename
import os
import uuid
from trac.versioncontrol.svn_fs import SvnCachedRepository, SubversionRepository

def is_subversion_repository(repo):
    ''' Checks if the repository is derived from SvnCachedRepository or 
    SubversionRepository. '''
    if isinstance(repo, (SvnCachedRepository, SubversionRepository)):
        return True
    return False

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
        return 6

    def get_draw_separator(self, req):
        return True
    
    def get_content(self, req, entry, data):
        # Make sure that repository is a Subversion repository.
        if not is_subversion_repository(data.get('repos')):
            return None

        if self.env.is_component_enabled("svnurls.svnurls.svnurls"):
            # They are already providing links to subversion, so we won't duplicate them.
            return None

        path = self.get_subversion_path(entry)
        href = self.get_subversion_href(data, path)

        return tag.a(_(tag.i(class_="icon-globe")),' Subversion URL', href=href, class_='external svn')

    def get_subversion_path(self, entry):
        if isinstance(entry, basestring):
            return entry
        else:
            try:
                return entry.path
            except AttributeError:
                return entry['path']

    def get_subversion_href(self, data, path):
        href = self.svn_base_url.rstrip('/')
        if data['reponame']:
            href += '/' + data['reponame']
        if path != '/':
            href += '/' + path
        return href

class TortoiseSvnLink(SubversionLink):
    """
    Generates a direct link to the file using the TortoiseSVN tsvncmd protocol.
    """
    implements(ISourceBrowserContextMenuProvider, IRequestHandler, 
                IRequestFilter, ITemplateProvider, ITemplateStreamFilter)

    # IContextMenuProvider methods
    def get_order(self, req):
        return 7

    def get_draw_separator(self, req):
        return True
    
    def get_content(self, req, entry, data):
        # Make sure that repository is a Subversion repository.
        if not is_subversion_repository(data.get('repos')):
            return None

        path = self.get_subversion_path(entry)
        href = self.get_subversion_href(data, path)

        # create a url which uses the tsvncmd protocol and repobrowser
        tortoise_href = "tsvncmd:command:repobrowser?path:" + href
        return tag.a(_(tag.i(class_="icon-code-fork")),' Browse With TortoiseSVN',
                                    href=tortoise_href, id_='browse-with-tortoise')

    # IRequestFilter Methods

    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        if req.path_info.startswith('/browser'):
            # see if the user has seen the tortoise svn dialog before
            # we use this data in the javascript to tell if we should 
            # show a dialog which asks the user if they have TSVN installed
            if 'tortoise_svn_message' in req.session:
                add_script_data(req, {'tortoise_svn_message': True})
            else:
                add_script_data(req, {'tortoise_svn_message': False})
                add_script(req, 'contextmenu/js/tortoise-svn-message.js')

        return template, data, content_type

    # IRequestHandler Methods

    def match_request(self, req):
        return req.path_info.startswith("/ajax/tortoise-svn-message")

    def process_request(self, req):
        """
        Sets a session attribute to show the user has seen the tortoise svn 
        repo browser dialog.

        This request will only ever be via a POST with Ajax. As a result, 
        if the request is a GET or does not have a XMLHttpRequest header 
        we redirect the user back to the browser page.

        Once the new session attribute is set, we send a JSON respsone. We 
        stop showing the dialog box when this attribute is set. 
        """

        if (req.method == "POST" and
          req.get_header('X-Requested-With') == 'XMLHttpRequest' and
          req.args.get('tortoise-svn-message')):
            req.session['tortoise_svn_message'] = True
            self.log.info("Set tortoise_svn_message session attribute "
                              "as True for %s", req.authname)
            req.session.save()
            req.send(to_json({"success":True}), 'text/json')
        else:
            # if you try to access this page via GET we redirect
            req.redirect(req.href.browser())

    # ITemplateProvider Methods

    def get_htdocs_dirs(self):
        return [('contextmenu', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []

    # ITemplateStreamFilter

    def filter_stream(self, req, method, filename, stream, data):
        if req.path_info.startswith('/browser') and not data.get('tortoise-svn-message'):
            # add a hidden dialog div for the tortoisve svn message
            message = tag.p("TortoiseSVN is a Windows explorer client you can use to browse your Subversion repository.",
                          tag.p("If you have not installed TortoiseSVN, you can download it now from the ",
                              tag.a("TortoiseSVN website.",
                                  href="http://tortoisesvn.net/downloads.html",
                                  target="_blank"
                              ),
                          ),
                          tag.p("If you have installed TortoiseSVN, please select continue.",
                          ),
                          tag.p("Please be aware that you may need to configure your proxy "
                                "before using TortoiseSVN. Also note that this message will "
                                "not appear again if you click continue.",
                            class_="info-light"
                          ),
                      )
            form =  tag.form(
                        tag.div(
                            tag.input(
                                type="hidden",
                                name="__FORM_TOKEN",
                                value=req.form_token
                            ),
                        ),
                        tag.input(
                            name="tortoise-svn-message",
                            value="True",
                        ),
                        id_="tortoise-svn-message-form",
                        class_="hidden"
                    )

            stream = stream | Transformer("//*[@id='dirlist']").after(tag.div(message, form,
                                                                                id_='tortoise-svn-message-dialog',
                                                                                class_='hidden'
                                                                             )
                                                                      )
        return stream

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
        
        for kind, data, pos in stream:
            if kind == START:
                if all((data[0] == QName("http://www.w3.org/1999/xhtml}table"),
                        data[1].get('id') == 'dirlist',
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
                    if  rows_seen == 1 and ('up' in self.data['chrome']['links'] or \
                                            (self.data['dir'] and not self.data['dir']['entries'])):
                        data = data[0], data[1] - 'colspan' | [(QName('colspan'), '7')]
                        yield kind, data, pos
                        continue # don't mess with the "parent link" and "No files found" row
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
                    menu = tag.div(tag.a(class_="ctx-expander icon-angle-down"),
                                   tag.div(
                                       tag.ul(class_="styled-dropdown"), 
                                       class_="bottom-fix"
                                   ),
                                   id="ctx-%s" % uid,
                                   class_="inline-block margin-left-small dropdown-toggle")

                    for provider in sorted(self.context_menu_providers, key=lambda x: x.get_order(self.req)):
                        entry = self.data['dir']['entries'][idx]
                        content = provider.get_content(self.req, entry, self.data)
                        if content:
                            menu.children[1].children[0].append(tag.li(content))
                    if len(menu.children[1].children[0].children) > 1:
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
            if not is_subversion_repository(data.get('repos')):
                #temporary control until we got something in place for non svn
                #repos.
                return stream
            # provide a link to the svn repository at the top of the Browse Source listing
            if self.env.is_component_enabled("contextmenu.contextmenu.SubversionLink"):
                add_ctxtnav(req, SubversionLink(self.env).get_content(req, data['path'], data), category='ctxtnav-list')
                add_ctxtnav(req, TortoiseSvnLink(self.env).get_content(req, data['path'], data), category='ctxtnav-list')
            stream |= ContextMenuTransformation(req, data, self.context_menu_providers)
        return stream
    
    # ITemplateProvider methods
    
    def get_htdocs_dirs(self):
        return [('contextmenu', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []
