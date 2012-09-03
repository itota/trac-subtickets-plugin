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

import re

import pkg_resources

from trac.core import *
from trac.env import IEnvironmentSetupParticipant
from trac.db import DatabaseManager
from trac.ticket.model import Ticket
from trac.ticket.api import ITicketChangeListener, ITicketManipulator

from trac.util.translation import domain_functions


import db_default


NUMBERS_RE = re.compile(r'\d+', re.U)

# i18n support for plugins, available since Trac r7705
# use _, tag_ and N_ as usual, e.g. _("this is a message text")
_, tag_, N_, add_domain = domain_functions('tracsubtickets', 
    '_', 'tag_', 'N_', 'add_domain')


class SubTicketsSystem(Component):

    implements(IEnvironmentSetupParticipant,
               ITicketChangeListener,
               ITicketManipulator)

    def __init__(self):
        self._version = None
        self.ui = None
        # bind the 'traccsubtickets' catalog to the locale directory
        locale_dir = pkg_resources.resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        self.found_db_version = 0
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        cursor = db.cursor()
        cursor.execute("SELECT value FROM system WHERE name=%s",
                       (db_default.name, ))
        value = cursor.fetchone()
        try:
            self.found_db_version = int(value[0])
            if self.found_db_version < db_default.version:
                return True
        except:
            self.found_db_version = 0
            return True

        # check the custom field
        if 'parents' not in self.config['ticket-custom']:
            return True

        return False

    def upgrade_environment(self, db):
        db_manager, _ = DatabaseManager(self.env)._get_connector()

        # update the version
        old_data = {} # {table.name: (cols, rows)}
        cursor = db.cursor()
        if not self.found_db_version:
            cursor.execute("INSERT INTO system (name, value) VALUES (%s, %s)",
                           (db_default.name, db_default.version))
        else:
            cursor.execute("UPDATE system SET value=%s WHERE name=%s",
                           (db_default.version, db_default.name))
            for table in db_default.tables:
                cursor.execute("SELECT * FROM %s", (table.name, ))
                cols = [x[0] for x in cursor.description],
                rows = cursor.fetchall()
                old_data[table.name] = (cols, rows)
                cursor.execute("DROP TABLE %s", (table.name))

        # insert the default table
        for table in db_default.tables:
            for sql in db_manager.to_sql(table):
                cursor.execute(sql)

            # add old data
            if table.name in old_data:
                cols, rows = old_data[table.name]
                sql = 'INSERT INTO %s (%s) VALUES (%s)' % \
                    (table.name, ','.join(cols), ','.join(['%s'] * len(cols)))
                for row in rows:
                    cursor.execute(sql, row)

        # add the custom field
        cfield = self.config['ticket-custom']
        if 'parents' not in cfield:
            cfield.set('parents', 'text')
            cfield.set('parents.label', 'Parent Tickets')
            self.config.save()

    # ITicketChangeListener methods
    def ticket_created(self, ticket):
        self.ticket_changed(ticket, '', ticket['reporter'], {'parents': ''})

    def ticket_changed(self, ticket, comment, author, old_values):
        if 'parents' not in old_values:
            return

        old_parents = old_values.get('parents', '') or ''
        old_parents = set(NUMBERS_RE.findall(old_parents))
        new_parents = set(NUMBERS_RE.findall(ticket['parents'] or ''))

        if new_parents == old_parents:
            return

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        # remove old parents
        for parent in old_parents - new_parents:
            cursor.execute("DELETE FROM subtickets WHERE parent=%s AND child=%s",
                           (parent, ticket.id))
            # add a comment to old parent
            xticket = Ticket(self.env, parent)
            xticket.save_changes(author, 'Remove a subticket #' + str(ticket.id) + '.')

        # add new parents
        for parent in new_parents - old_parents:
            cursor.execute("INSERT INTO subtickets VALUES(%s, %s)",
                           (parent, ticket.id))
            # add a comment to new parent
            xticket = Ticket(self.env, parent)
            xticket.save_changes(author, 'Add a subticket #' + str(ticket.id) + '.')

        db.commit()

    def ticket_deleted(self, ticket):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        # TODO: check if there's any child ticket
        cursor.execute("DELETE FROM subtickets WHERE child=%s", (ticket.id, ))
        db.commit()

    # ITicketManipulator methods
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def validate_ticket(self, req, ticket):
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        try:
            ids = []
            _ids = set(NUMBERS_RE.findall(ticket['parents'] or ''))
            myid = str(ticket.id)
            for id in _ids:
                if id == myid:
                    yield 'parents', _('A ticket cannot be a parent to itself')
                else:
                    # check if the id exists
                    cursor.execute("SELECT id FROM ticket WHERE id=%s", (id, ))
                    row = cursor.fetchone()
                    if row is None:
                        yield 'parents', _('Ticket #%s does not exist') % id
                ids.append(id)

            # circularity check function
            def _check_parents(id, all_parents):
                all_parents = all_parents + [id]
                errors = []
                cursor.execute("SELECT parent FROM subtickets WHERE child=%s", (id, ))
                for x in [int(x[0]) for x in cursor]:
                    if x in all_parents:
                        error = ' > '.join(['#%s' % n for n in all_parents + [x]])
                        errors.append(('parents', _('Circularity error: %s') % error))
                    else:
                        errors += _check_parents(x, all_parents)
                return errors

            for x in ids:
                # check parent ticket state
                parent = Ticket(self.env, x)
                if parent and parent['status'] == 'closed':
                    yield 'parents', _('Parent ticket #%s is closed') % x
                else:
                    # check circularity
                    all_parents = ticket.id and [ticket.id] or []
                    for error in _check_parents(int(x), all_parents):
                        yield error

            ticket['parents'] = ', '.join(sorted(ids, key=lambda x: int(x)))

        except Exception, e:
            self.log.error(e)
            yield 'parents', _('Not a valid list of ticket IDs')

