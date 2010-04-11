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

import sys
from optparse import OptionParser
from trac.env import open_environment

from api import NUMBERS_RE


def check_subtickets(env):
    db = env.get_db_cnx()
    cursor = db.cursor()

    cfield = {}
    cursor.execute("SELECT ticket, value FROM ticket_custom WHERE name='parents'")
    for row in cursor:
        id = row[0]
        parents = [int(x) for x in NUMBERS_RE.findall(row[1])]
        cfield[id] = parents

    subtickets = {}
    cursor.execute("SELECT parent, child FROM subtickets")
    for row in cursor:
        parent = int(row[0])
        child = int(row[1])
        if child in subtickets:
            subtickets[child] += [parent]
        else:
            subtickets[child] = [parent]

    for id in set(cfield.keys() + subtickets.keys()):
        result = False
        if id in cfield and id in subtickets:
            cfield_values = set(cfield[id])
            subtickets_values = set(subtickets[id])
            if cfield_values == subtickets_values:
                result = True
        elif id not in subtickets:
            if not cfield.get(id):
                result = True

        if not result:
            print "Mismatch in ticket #%i" % id
            print "  custom field :", cfield.get(id, '--')
            print "  subtickets   :", subtickets.get(id, '--')


def main(args=sys.argv[1:]):
    parser = OptionParser('%prog [options] project <project2> <project3> ...')
    options, args = parser.parse_args(args)

    # if no projects, print usage
    if not args:
        parser.print_help()
        sys.exit(0)

    # get the environments
    envs = []
    for arg in args:
        env = open_environment(arg)
        envs.append(env)

    # check all the environments
    for env in envs:
        check_subtickets(env)


if __name__ == '__main__':
    main()

