#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2013-2016 Alberto Gacías <alberto@migasfree.org>
# Copyright (c) 2015-2016 Jose Antonio Chavarría <jachavar@gmail.com>
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

__author__ = [
    'Alberto Gacías <alberto@migasfree.org>',
    'Jose Antonio Chavarría <jachavar@gmail.com>'
]
__license__ = 'GPLv3'
__copyright__ = '(C) 2010-2016 migasfree team'

import os
import sys
import threading
import locale
import subprocess
import webbrowser
import optparse
import time
import errno

import gettext
_ = gettext.gettext

from gi import require_version
require_version('Gtk', '3.0')
require_version('AppIndicator3', '0.1')

from gi.repository import (
    Gio,
    GObject,
    Gtk,
    AppIndicator3 as AppIndicator,
)

version_file = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'VERSION'
)
if not os.path.exists(version_file):
    version_file = os.path.join(
        sys.prefix,
        'share',
        'doc',
        'migasfree-launcher',
        'VERSION'
    )

__version__ = open(version_file).read().splitlines()[0]

from migasfree_client.utils import execute
from migasfree_client.utils import get_config
from migasfree_client.network import get_gateway

from .console import Console

CONF_FILE = "/etc/migasfree-indicator.conf"
WAIT_IP_TIMEOUT = 120  # 2 min
DEFAULT_INTERVAL = 24  # hours


def has_ip_address():
    _cont = WAIT_IP_TIMEOUT
    while (get_gateway() is None or get_gateway() == '') and _cont > 0:
        time.sleep(1)
        _cont -= 1

    return get_gateway() != '' and get_gateway() is not None


class SystrayIconApp(object):
    APP_INDICATOR_ID = 'migasfree-indicator'
    APP_NAME = _('Migasfree Indicator')
    APP_DESCRIPTION = _('Indicator to view and control migasfree client actions')

    SCHEMA = "org.migasfree.console"
    SHOW_CONSOLE = "show-console"

    CMD_UPGRADE = "sudo migasfree-launcher"
    CMD_FORCE_UPGRADE = "sudo migasfree-launcher force-upgrade"
    CMD_LABEL = "migasfree-label"

    FIRST_RUN = "/var/tmp/migasfree/first-tags.conf"

    def __init__(self, options):
        if options.interval:
            self.interval = options.interval * 3600000
        else:
            self.interval = DEFAULT_INTERVAL * 3600000

        if options.support:
            self.support = options.support
        else:
            self.support = ''

        self.is_force_upgrade = (options.force_upgrade is True)

        self.console = Console()
        if os.path.isfile(self.FIRST_RUN):
            self.console.show_all()

        self.is_upgrading = False

        self.fore_color = self.get_fore_color()
        self.icon = 'migasfree-idle-%s' % self.fore_color

        self.tray = AppIndicator.Indicator.new(
            self.APP_INDICATOR_ID,
            self.icon,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.tray.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.tray.set_attention_icon('attention_icon')
        GObject.idle_add(self.tray.set_icon, self.icon)

        self.mode_console = self.get_console()
        self.make_menu()

        self.update_system()
        GObject.timeout_add(self.interval, self.update_system)
        GObject.timeout_add(10000, self.check_reboot)

    @staticmethod
    def get_fore_color():
        _menu = Gtk.Menu()
        _bg_color = _menu.get_style_context().get_background_color(
            Gtk.StateFlags.NORMAL
        )
        if (_bg_color.red + _bg_color.green + _bg_color.blue) / 3 > .5:
            return 'light'

        return 'dark'

    def make_menu(self):
        self.menu = Gtk.Menu()

        self.menu_force_upgrade = Gtk.ImageMenuItem(
            _('Force Upgrade')
        )
        self.menu_force_upgrade.set_image(
            self.get_image("migasfree-force-upgrade")
        )
        GObject.idle_add(self.menu_force_upgrade.set_sensitive, not self.is_upgrading)
        self.menu_force_upgrade.show()
        self.menu_force_upgrade.connect('activate', self.force_upgrade)
        self.menu.append(self.menu_force_upgrade)

        self.menu.append(Gtk.SeparatorMenuItem())

        _menu_console = Gtk.ImageMenuItem(_('Console'))
        _menu_console.set_image(self.get_image("migasfree-console"))
        _menu_console.show()
        _menu_console.connect('activate', self.show_console)
        self.menu.append(_menu_console)

        _menu_mode_console = Gtk.CheckMenuItem(_('Show console always'))
        _menu_mode_console.connect('activate', self.on_show_console)
        _menu_mode_console.set_active(self.mode_console)
        self.menu.append(_menu_mode_console)

        self.menu.append(Gtk.SeparatorMenuItem())

        _label_id = Gtk.ImageMenuItem(_('Identification label'))
        _label_id.set_image(self.get_image("migasfree-label"))
        _label_id.show()
        _label_id.connect('activate', self.show_label_id)
        self.menu.append(_label_id)

        if self.support:
            _support = Gtk.ImageMenuItem(_('Support'))
            _support.set_image(self.get_image("migasfree-support"))
            _support.show()
            _support.connect('activate', self.show_support)
            self.menu.append(_support)

        self.menu.append(Gtk.SeparatorMenuItem())

        _about = Gtk.ImageMenuItem(_('About'))
        _about.set_image(self.get_image('help-about'))
        _about.show()
        _about.connect('activate', self.show_about)
        self.menu.append(_about)

        self.menu.show_all()
        self.tray.set_menu(self.menu)

    def set_console(self, value):
        _settings = Gio.Settings.new(self.SCHEMA)
        _settings.set_boolean(self.SHOW_CONSOLE, value)

    def get_console(self):
        _settings = Gio.Settings.new(self.SCHEMA)

        return _settings.get_boolean(self.SHOW_CONSOLE)

    def on_show_console(self, widget):
        self.set_console(widget.get_active())
        self.mode_console = widget.get_active()

    @staticmethod
    def get_image(name):
        _img = Gtk.Image()
        _img.set_from_icon_name(name, Gtk.IconSize.MENU)

        return _img

    def show_console(self, widget):
        if self.console.get_property("visible"):
            self.console.hide()
        else:
            self.console.show_all()

    def show_label_id(self, widget):
        os.system(self.CMD_LABEL)

    def show_support(self, widget):
        webbrowser.open(self.support)

    def show_about(self, widget):
        about = Gtk.AboutDialog()

        about.set_destroy_with_parent(True)
        about.set_program_name(self.APP_NAME)
        about.set_comments(self.APP_DESCRIPTION)
        about.set_icon_name('migasfree')
        about.set_logo_icon_name('migasfree')
        about.set_name(__file__)
        about.set_version(__version__)
        about.set_copyright(__copyright__)
        about.set_authors(__author__)
        about.set_website("http://migasfree.org/")
        about.set_website_label("migasfree.org")

        about.run()
        about.destroy()

    def upgrade(self, widget):
        self.run_command(self.CMD_UPGRADE)

    def force_upgrade(self, widget):
        self.run_command(self.CMD_FORCE_UPGRADE)

    def update_system(self):
        if not self.is_upgrading:
            if self.is_force_upgrade:
                self.force_upgrade(None)
            else:
                self.upgrade(None)

        return True

    def cmd_reboot(self):
        ret, _, _ = execute('which ck-list-sessions')
        if ret == 0:
            cmd = 'dbus-send --system --print-reply '
            '--dest=org.freedesktop.ConsoleKit '
            '/org/freedesktop/ConsoleKit/Manager '
            'org.freedesktop.ConsoleKit.Manager.Restart'
        else:
            cmd = 'dbus-send --system --print-reply '
            '--dest=org.freedesktop.login1 '
            '/org/freedesktop/login1 '
            '"org.freedesktop.login1.Manager.Reboot" boolean:true'

        execute(cmd, interactive=True, verbose=True)

    def check_reboot(self):
        if not self.is_upgrading \
                and os.path.isfile('/var/run/reboot-required'):
            GObject.idle_add(self.tray.set_icon, 'dialog-warning')

            _menu_reboot = Gtk.ImageMenuItem(
                _('Restart your computer to finish updating the system')
            )
            _menu_reboot.set_image(self.get_image('dialog-warning'))
            _menu_reboot.show()
            _menu_reboot.connect('activate', self.reboot_computer)
            self.menu.append(_menu_reboot)

            GObject.idle_add(self.menu_force_upgrade.set_sensitive, False)

            return False

        return True

    def reboot_computer(self, widget):
        self.cmd_reboot()

    def run_command(self, command):
        self.console.textbuffer.set_text('')
        if self.mode_console:
            self.console.show_all()

        thread = threading.Thread(
            target=self.read_output,
            args=(command,)
        )
        thread.setDaemon(True)
        thread.start()

    def read_output(self, command):
        self.is_upgrading = True

        GObject.idle_add(self.menu_force_upgrade.set_sensitive,False)
        self.console.timeout_id = GObject.timeout_add(
            50,
            self.console.on_timeout,
            None
        )

        GObject.idle_add(self.tray.set_icon, 'migasfree')

        _process = subprocess.Popen(
            command.split(" "),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        while _process.returncode is None:
            try:
                _line = _process.stdout.readline()
            except:
                _line = ''

            if not _line and _process.poll() is not None:
                break

            _line = self.clean_text(_line)
            GObject.idle_add(self.add_text_to_console, _line)

        self.update_tray_icon(_process.returncode)
        self.is_upgrading = False
        GObject.idle_add(self.menu_force_upgrade.set_sensitive, True)
        self.console.progress.set_fraction(0)

        if self.console.timeout_id:
            GObject.source_remove(self.console.timeout_id)
            self.console.timeout_id = 0

    def update_tray_icon(self, return_code):
        if return_code == errno.ECONNREFUSED:
            self.icon = 'migasfree-error-%s' % self.fore_color
        elif return_code != os.EX_OK:
            self.icon = 'migasfree-warning-%s' % self.fore_color
        else:
            self.icon = 'migasfree-idle-%s' % self.fore_color

        GObject.idle_add(self.tray.set_icon, self.icon)

    @staticmethod
    def clean_text(text):
        return text.replace("\033[92m", "").replace(
            "\033[91m", ""
        ).replace("\033[32m", "").replace("\033[0m", "")

    def add_text_to_console(self, line):
        _encoding = locale.getpreferredencoding()
        _utf8conv = lambda x: unicode(x, _encoding).encode('utf8')

        _iterator = self.console.textbuffer.get_end_iter()
        self.console.textbuffer.place_cursor(_iterator)
        self.console.textbuffer.insert(_iterator, _utf8conv(line))
        self.console.textview.scroll_to_mark(
            self.console.textbuffer.get_insert(),
            0.1, False, 0, 0
        )

    def run(self):
        GObject.threads_init()
        Gtk.main()


def main():
    locale.setlocale(locale.LC_ALL, '.'.join(locale.getdefaultlocale()))
    gettext.textdomain('migasfree-launcher')

    config = get_config(CONF_FILE, 'indicator')
    if isinstance(config, dict):
        config = {}

    if not has_ip_address():
        print(_('No network access'))
        sys.exit(1)

    parser = optparse.OptionParser(
        description=__file__,
        prog=__file__,
        version=__version__,
        usage='%prog options'
    )

    parser.add_option(
        "--force-upgrade",
        "-a",
        action="store_true",
        help=_('Force Upgrade'),
        default=config.get('force_upgrade', False),
    )
    parser.add_option(
        "--interval",
        "-i",
        type="int",
        default=config.get('interval', DEFAULT_INTERVAL),
    )
    parser.add_option(
        "--support",
        "-s",
        action="store",
        default=config.get('support', ''),
    )

    options, arguments = parser.parse_args()

    SystrayIconApp(options).run()


if __name__ == "__main__":
    main()
