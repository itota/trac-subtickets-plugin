#!/usr/bin/python
#
# Copyright (c) 2010, Takashi Ito
# i18n and German translation by Steffen Hoffmann
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

from setuptools import find_packages, setup

setup(
    name = 'TracSubTicketsPlugin',
    version = '0.1.1',
    keywords = 'trac plugin ticket subticket',
    author = 'Takashi Ito',
    author_email = 'TakashiC.Ito@gmail.com',
    url = 'http://github.com/itota/trac-subtickets-plugin',
    description = 'Trac Sub-Tickets Plugin',
    long_description = """
    This plugin for Trac 0.12 provides Sub-Tickets functionality.

    The association is done by adding parent tickets number to a custom field.
    Checks ensure i.e. resolving of sub-tickets before closing the parent.
    Babel is required to display localized texts.
    Currently only translation for de_DE is provided.
    """
    license = 'BSD',

    install_requires = ['Trac >= 0.12dev'],

    packages = find_packages(exclude=['*.tests*']),
    package_data = {
        'tracsubtickets': [
            'htdocs/css/*.css',
            'locale/*.*',
            'locale/*/LC_MESSAGES/*.*',
        ],
    },
    entry_points = {
        'trac.plugins': [
            'tracsubtickets.api = tracsubtickets.api',
            'tracsubtickets.web_ui = tracsubtickets.web_ui',
        ],
        'console_scripts': [
            'check-trac-subtickets = tracsubtickets.checker:main',
        ],
    },
)
