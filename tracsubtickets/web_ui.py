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
from trac.web.api import IRequestFilter
from trac.ticket.api import ITicketManipulator
from trac.ticket.model import Ticket
from genshi.builder import tag

from api import SubTicketsSystem


class SubTicketsModule(Component):

    implements(IRequestFilter, ITicketManipulator)

    NUMBERS_RE = SubTicketsSystem.NUMBERS_RE

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        if req.path_info.startswith('/ticket/'):
            # get parents data
            parents = data['ticket']['parents'] or ''
            ids = set(self.NUMBERS_RE.findall(parents))

            if len(parents) > 0:
                self._append_parent_links(req, data, ids)

        return template, data, content_type

    def _append_parent_links(self, req, data, ids):
        links = []
        for id in ids:
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
        
    def validate_ticket(self, req, ticket):
        if req.args.get('action') == 'resolve':
            db = self.env.get_db_cnx()
            cursor = db.cursor()

            cursor.execute("SELECT parent, child FROM subtickets WHERE parent=%s",
                           (ticket.id, ))

            for parent, child in cursor:
                if Ticket(self.env, child)['status'] != 'closed':
                    yield None, 'Child ticket #%s has not been closed yet' % child

        elif req.args.get('action') == 'reopen':
            ids = set(self.NUMBERS_RE.findall(ticket['parents'] or ''))
            for id in ids:
                if Ticket(self.env, id)['status'] == 'closed':
                    yield None, 'Parent ticket #%s is closed' % id

