#!/usr/bin/python
#
# Copyright (c) 2010, Takashi Ito
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the authors nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from trac.core import *
from trac.web.api import IRequestFilter, ITemplateStreamFilter
from trac.web.chrome import ITemplateProvider, add_stylesheet
from trac.ticket.api import ITicketManipulator
from trac.ticket.model import Ticket
from genshi.builder import tag
from genshi.filters import Transformer

from api import NUMBERS_RE, _


class SubTicketsModule(Component):

    implements(ITemplateProvider,
               IRequestFilter,
               ITicketManipulator,
               ITemplateStreamFilter)

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('subtickets', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        path = req.path_info
        if path.startswith('/ticket/') or path.startswith('/newticket'):
            # get parents data
            ticket = data['ticket']
            parents = ticket['parents'] or ''
            ids = set(NUMBERS_RE.findall(parents))

            if len(parents) > 0:
                self._append_parent_links(req, data, ids)

            children = self.get_children(ticket.id)
            if children:
                data['subtickets'] = children

        return template, data, content_type

    def _append_parent_links(self, req, data, ids):
        links = []
        for id in sorted(ids, key=lambda x: int(x)):
            ticket = Ticket(self.env, id)
            elem = tag.a('#%s' % id,
                         href=req.href.ticket(id),
                         class_='%s ticket' % ticket['status'],
                         title=ticket['summary'])
            if len(links) > 0:
                links.append(', ')
            links.append(elem)
        for field in data.get('fields', ''):
            if field.get('name') == 'parents':
                field['rendered'] = tag.span(*links)

    # ITicketManipulator methods
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def get_children(self, parent_id, db=None):
        children = {}
        if not db:
            db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT parent, child FROM subtickets WHERE parent=%s",
                       (parent_id, ))

        for parent, child in cursor:
            children[child] = None

        for id in children:
            children[id] = self.get_children(id, db)

        return children

    def validate_ticket(self, req, ticket):
        action = req.args.get('action')
        if action == 'resolve':
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("SELECT parent, child FROM subtickets WHERE parent=%s",
                           (ticket.id, ))

            for parent, child in cursor:
                if Ticket(self.env, child)['status'] != 'closed':
                    yield None, _('Child ticket #%s has not been closed yet') % child

        elif action == 'reopen':
            ids = set(NUMBERS_RE.findall(ticket['parents'] or ''))
            for id in ids:
                if Ticket(self.env, id)['status'] == 'closed':
                    yield None, _('Parent ticket #%s is closed') % id

    # ITemplateStreamFilter method
    def filter_stream(self, req, method, filename, stream, data):
        if req.path_info.startswith('/ticket/'):
            div = None
            if 'ticket' in data:
                # get parents data
                ticket = data['ticket']
                # title
                div = tag.div(class_='description')
                if ticket['status'] != 'closed':
                    link = tag.a(_('add'),
                        href=req.href.newticket(parents=ticket.id),
                        title=_('Create new child ticket'))
                    link = tag.span('(', link, ')', class_='addsubticket')
                else:
                    link = None
                div.append(tag.h3(_('Subtickets '), link))

            if 'subtickets' in data:
                # table
                tbody = tag.tbody()
                div.append(tag.table(tbody, class_='subtickets'))

                # tickets
                def _func(children, depth=0):
                    for id in sorted(children, key=lambda x: int(x)):
                        ticket = Ticket(self.env, id)

                        # 1st column
                        attrs = {'href': req.href.ticket(id)}
                        if ticket['status'] == 'closed':
                            attrs['class_'] = 'closed'
                        link = tag.a('#%s' % id, **attrs)
                        summary = tag.td(link, ': %s' % ticket['summary'],
                            style='padding-left: %dpx;' % (depth * 15))
                        # 2nd column
                        type = tag.td(ticket['type'])
                        # 3rd column
                        status = tag.td(ticket['status'])
                        # 4th column
                        href = req.href.query(status='!closed',
                                              owner=ticket['owner'])
                        owner = tag.td(tag.a(ticket['owner'], href=href))

                        tbody.append(tag.tr(summary, type, status, owner))
                        _func(children[id], depth + 1)

                _func(data['subtickets'])

            if div:
                add_stylesheet(req, 'subtickets/css/subtickets.css')
                stream |= Transformer('.//div[@id="ticket"]').append(div)

        return stream

