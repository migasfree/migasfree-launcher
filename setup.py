#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright (c) 2016 Jose Antonio Chavarrí­a <jachavar@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import glob
import subprocess

from setuptools import setup, find_packages
from distutils.command.build import build
from distutils.command.install_data import install_data
from distutils.log import info, error
from distutils.dep_util import newer

PATH = os.path.dirname(os.path.abspath(__file__))
README = open(os.path.join(PATH, 'README.md')).read()
VERSION = open(os.path.join(PATH, 'VERSION')).read().splitlines()[0]
APP_NAME = 'migasfree-launcher'

PO_DIR = 'i18n'
MO_DIR = os.path.join('build', 'mo')


class BuildData(build):
    def run(self):
        build.run(self)

        for po in glob.glob(os.path.join(PO_DIR, '*.po')):
            lang = os.path.basename(po[:-3])
            mo = os.path.join(MO_DIR, lang, '%s.mo' % APP_NAME)

            directory = os.path.dirname(mo)
            if not os.path.exists(directory):
                info('creating %s' % directory)
                os.makedirs(directory)

            if newer(po, mo):
                info('compiling %s -> %s' % (po, mo))
                try:
                    rc = subprocess.call(['msgfmt', '-o', mo, po])
                    if rc != 0:
                        raise Warning("msgfmt returned %d" % rc)
                except Exception, e:
                    error("Building gettext files failed.  Try setup.py \
                        --without-gettext [build|install]")
                    error("Error: %s" % str(e))
                    sys.exit(1)


class InstallData(install_data):
    def run(self):
        self.data_files.extend(self._find_mo_files())
        install_data.run(self)

    def _find_mo_files(self):
        data_files = []

        for mo in glob.glob(os.path.join(MO_DIR, '*', '%s.mo' % APP_NAME)):
            lang = os.path.basename(os.path.dirname(mo))
            dest = os.path.join('share', 'locale', lang, 'LC_MESSAGES')
            data_files.append((dest, [mo]))

        return data_files


setup(
    name = APP_NAME,
    version = VERSION,
    packages = find_packages(),
    data_files = [
        ('share/doc/migasfree-launcher', [
            'AUTHORS',
            'INSTALL',
            'LICENSE',
            'README.md',
            'VERSION',
        ]),
        ('share/applications', ['data/migasfree-indicator.desktop']),
        ('/etc/xdg/autostart', ['data/migasfree-indicator.desktop']),
        ('share/icons/hicolor/scalable/apps', [
            'data/img/migasfree-apps.svg',
            'data/img/migasfree-console.svg',
            'data/img/migasfree-error-dark.svg',
            'data/img/migasfree-error-light.svg',
            'data/img/migasfree-force-upgrade.svg',
            'data/img/migasfree-idle-dark.svg',
            'data/img/migasfree-idle-light.svg',
            'data/img/migasfree-label.svg',
            'data/img/migasfree-support.svg',
            'data/img/migasfree-warning-dark.svg',
            'data/img/migasfree-warning-light.svg',
        ]),
        ('share/glib-2.0/schemas', ['data/org.migasfree.tray.gschema.xml']),
        ('/etc', ['data/migasfree-indicator.conf']),
        ('/etc/sudoers.d', ['data/sudo/migasfree-launcher']),
    ],
    scripts=[
        'bin/migasfree-launcher',
    ],
    cmdclass={
        'build': BuildData,
        'install_data': InstallData,
    },
    author = 'Jose Antonio Chavarría',
    author_email = 'jachavar@gmail.com',
    license = 'GPLv3',
    platforms = ['Linux'],
    long_description = README,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: Gnome',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Utilities',
        'Topic :: Desktop Environment :: Gnome',
        'Topic :: Utilities',
    ],
    entry_points = {
        'console_scripts': [
            'migasfree-indicator=migasfree_indicator.command_line:main'
        ],
    },
)
