#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014-2016 Alberto Gacías <alberto@migasfree.org>
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

import gettext
_ = gettext.gettext

from gi.repository import Gtk


class Console(Gtk.Window):
    def __init__(self):
        super(Console, self).__init__()

        sw = Gtk.ScrolledWindow()
        sw.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )
        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self.textview.set_editable(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        sw.add(self.textview)

        self.set_title(_('Migasfree Console'))
        self.set_icon_name('migasfree')
        self.resize(640, 420)
        self.set_decorated(True)
        self.set_border_width(10)

        self.connect('delete-event', self.on_click_hide)

        box = Gtk.Box(spacing=6, orientation='vertical')
        box.pack_start(sw, expand=True, fill=True, padding=0)

        self.progress = Gtk.ProgressBar()
        self.progress.set_pulse_step(0.02)
        progress_box = Gtk.Box(False, 0, orientation='vertical')
        progress_box.pack_start(self.progress, False, True, 0)
        box.pack_start(progress_box, expand=False, fill=True, padding=0)

        self.add(box)

    def on_timeout(self, user_data):
        self.progress.pulse()
        return True

    def on_click_hide(self, widget, data=None):
        self.hide()
        return True
