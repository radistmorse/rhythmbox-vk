# -*- coding: utf8 -*-
# Copyright © 2013 Radist Morse <radist.morse@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import RB, Gio, Gtk, GdkPixbuf, GObject, Peas, PeasGtk
import rb #"Loader" heler class
from xml.dom import minidom #xml parser
import urllib2 #search line escaping
import hashlib #search line hashing
from html_decode import decode_htmlentities #results decoding

import gettext
gettext.install('rhythmbox', RB.locale_dir())

#entry type for results. not saving on disk
class VKEntryType(RB.RhythmDBEntryType):
	def __init__(self):
		RB.RhythmDBEntryType.__init__(self, name="vk-entry-type", save_to_disk=False)
	def can_sync_metadata(self, entry):
		return False
	def do_sync_metadata(self, entry, changes):
		return

class VKRhythmbox(GObject.Object, Peas.Activatable):
	__gtype_name = 'VKRhythmboxPlugin'
	object = GObject.property(type=GObject.GObject)

	def __init__(self):
		GObject.Object.__init__(self)
			
	def do_activate(self):
		print "activating vk plugin"
		#connecting to GSettings
		schema_source = Gio.SettingsSchemaSource.new_from_directory(self.plugin_info.get_data_dir(), Gio.SettingsSchemaSource.get_default(), False,)
		schema = schema_source.lookup('org.gnome.rhythmbox.plugins.vk', False)
		self.settings = Gio.Settings.new_full(schema, None, None)
		#system settings
		shell = self.object
		db = shell.props.db
		model = RB.RhythmDBQueryModel.new_empty(db)
		vk_entry_type = VKEntryType()
		self.entry_type = vk_entry_type
		db.register_entry_type(vk_entry_type)
		#icon
		what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
		icon = GdkPixbuf.Pixbuf.new_from_file_at_size(self.plugin_info.get_data_dir()+"/vk.png", width, height)
		#create Source (aka tab)
		self.source = GObject.new (VKSource, shell=shell, name="VK "+_("Music"), query_model=model, entry_type=vk_entry_type, plugin=self, pixbuf=icon)
		self.source.setup(db, self.settings)
		shell.register_entry_type_for_source(self.source, vk_entry_type)
		#append source to the library
		group = RB.DisplayPageGroup.get_by_id ("library")
		shell.append_display_page(self.source, group)

	def do_deactivate(self):
		print "deactivating vk plugin"
		self.source.delete_thyself()
		self.source = None
		self.settings = None
		self.entry_type = None

#Source is the tab, the "main window"
class VKSource(RB.BrowserSource):
	def __init__(self, **kwargs):
		super(VKSource, self).__init__(kwargs)
	#callbacks for monitoring GSettings change
	def on_secret_key_changed(self, settings, key):
		self.SECRET_KEY = settings.get_string(key)
	def on_user_id_changed(self, settings, key):
		self.USER_ID = settings.get_string(key)
	def on_api_id_changed(self, settings, key):
		self.API_ID = settings.get_string(key)
	def on_amount_changed(self, settings, key):
		self.AMOUNT = settings.get_int(key)
		self.search_amount.set_text(str(self.AMOUNT))
		

	def setup(self, db, settings):
		self.db = db
		self.settings = settings
		#initial GSettings values
		self.SECRET_KEY = self.settings.get_string('secret')
		self.USER_ID = self.settings.get_string('user-id')
		self.API_ID = self.settings.get_string('api-id')
		self.AMOUNT =  self.settings.get_int('amount')
		#monitoring callbacks
		self.settings.connect("changed::secret", self.on_secret_key_changed)
		self.settings.connect("changed::user-id", self.on_user_id_changed)
		self.settings.connect("changed::api-id", self.on_api_id_changed)
		self.settings.connect("changed::amount", self.on_amount_changed)
		#UI setup
		search_line = Gtk.HBox()
		search_input = Gtk.Entry()
		search_line.pack_start(search_input, expand=True, fill=True, padding=2)
		search_button = Gtk.Button(_("Search"))
		search_line.pack_start(search_button, expand=False, fill=False, padding=2)
		search_amount_label = Gtk.Label(_("#"))
		search_amount_label.set_margin_left(10)
		search_line.pack_start(search_amount_label, expand=False, fill=False, padding=0)
		self.search_amount = Gtk.Entry(width_chars=7)
		self.search_amount.set_text(str(self.AMOUNT))
		self.search_amount.set_margin_right(10)
		search_line.pack_start(self.search_amount, expand=False, fill=False, padding=0)
		clear_button = Gtk.Button(_("Clear"))
		search_line.pack_start(clear_button, expand=False, fill=False, padding=2)
		#buttons actions
		search_button.connect("clicked", self.search_button_clicked, search_input, self.search_amount)
		clear_button.connect("clicked", self.clear_button_clicked)

		search_line.show_all()
		#place "our" UI to the Source. Removing unneeded GtkToolbar.
		self.get_children()[0].get_children()[1].get_children()[1].destroy()
		self.get_children()[0].get_children()[1].attach_next_to(search_line,self.get_children()[0].get_children()[1].get_children()[0],Gtk.PositionType.LEFT, 3, 1)

	def search_button_clicked(self, button, s_input, s_amount) :
		search_line = s_input.get_text()
		search_num = s_amount.get_text()
		try :
			search_num = int(search_num)
			self.settings.set_int("amount",search_num)
			self.AMOUNT = search_num
		except :
			search_num = self.AMOUNT
		# Only do anything if there is text in the search entry
		if len(search_line) > 0 :
			search = VkontakteSearch(search_line, str(search_num), self.db, self.props.entry_type, self.props.query_model, self.USER_ID, self.API_ID, self.SECRET_KEY)
			search.start()

	def clear_button_clicked(self, button) :
		#remove all VKEntryType entries from the db
		self.props.shell.props.db.entry_delete_by_type(self.props.entry_type)
		self.props.shell.props.db.commit()

	def do_impl_delete_thyself(self):
		if self.initialised:
			self.props.shell.props.db.entry_delete_by_type(self.props.entry_type)
			self.props.shell.props.db.commit()
		RB.Source.do_impl_delete_thyself(self)

GObject.type_register(VKSource)

class XMLResult:
	def __init__(self, entry):
		# Store the function. This will be called when we are ready to be added to the db.
		self.title = entry.getElementsByTagName('title')[0].firstChild.nodeValue.strip()
		self.duration = int(entry.getElementsByTagName('duration')[0].firstChild.nodeValue)
		self.artist = entry.getElementsByTagName('artist')[0].firstChild.nodeValue.strip()
		self.url = entry.getElementsByTagName('url')[0].firstChild.nodeValue

class VkontakteSearch:
	def __init__(self, search_line, search_num, db, entry_type, query_model, USER_ID, API_ID, SECRET_KEY):
		self.search_line = search_line
		self.search_num = search_num
		self.db = db
		self.entry_type = entry_type
		self.query_model = query_model
		self.entries_hashes = []
		self.USER_ID = USER_ID
		self.API_ID = API_ID
		self.SECRET_KEY = SECRET_KEY

	def make_sig(self, method, query, amount, USER_ID, API_ID, SECRET_KEY):
		str = "%sapi_id=%scount=%smethod=%sq=%stest_mode=1v=2.0%s" % (USER_ID, API_ID, amount, method, query, SECRET_KEY)
		return hashlib.md5(str).hexdigest()
		
	def add_entry(self, result):
		# add only distinct songs (unique by title+artist+duration) to prevent duplicates
		strhash = ('%s%s%s' % (result.title, result.artist, result.duration)).lower()
		if strhash in self.entries_hashes:
			return

		self.entries_hashes.append(strhash)
		#first, let's try to find if the song with this url is already in db
		entry = self.db.entry_lookup_by_location(result.url)
		if entry is None :
			#add song to db
			entry = RB.RhythmDBEntry.new(self.db, self.entry_type, result.url)
		if entry is not None :
			#update metadata
			self.db.entry_set(entry, RB.RhythmDBPropType.TITLE, decode_htmlentities(result.title).encode("utf-8"))
			self.db.entry_set(entry, RB.RhythmDBPropType.DURATION, result.duration)
			self.db.entry_set(entry, RB.RhythmDBPropType.ARTIST, decode_htmlentities(result.artist).encode("utf-8"))
			#all the songs will get "vk.com" album
			self.db.entry_set(entry, RB.RhythmDBPropType.ALBUM, "vk.com".encode("utf-8"))

	def on_search_results_recieved(self, data):
		data = data.decode("utf-8")
		# vkontakte sometimes returns invalid XML with empty first line
		data = data.lstrip()
		# remove invalid symbol that occured in titles/artist
		data = data.replace(u'\uffff', '')
		xmldoc = minidom.parseString(data.encode("utf-8"))
		audios = xmldoc.getElementsByTagName("audio")
		for audio in audios:
			self.add_entry(XMLResult(audio))
		self.db.commit()

	# Starts searching
	def start(self):
		sig = self.make_sig('audio.search', self.search_line, self.search_num, self.USER_ID, self.API_ID, self.SECRET_KEY)
		path = "http://api.vk.com/api.php?api_id=%s&count=%s&v=2.0&method=audio.search&sig=%s&test_mode=1&q=%s" % (self.API_ID, self.search_num, sig, urllib2.quote(self.search_line))
		loader = rb.Loader()
		loader.get_url(path, self.on_search_results_recieved)

#The class which deals with config window
class VKRhythmboxConfig(GObject.Object, PeasGtk.Configurable):
	__gtype_name__ = 'VKRhythmboxConfig'
	object = GObject.property(type=GObject.GObject)

	def __init__(self):
		GObject.GObject.__init__(self)

	#the most interesting function, which is called when user presses "configure". should return a widget
	def do_create_configure_widget(self):
		#connect to GSettings
		schema_source = Gio.SettingsSchemaSource.new_from_directory(self.plugin_info.get_data_dir(), Gio.SettingsSchemaSource.get_default(), False,)
		schema = schema_source.lookup('org.gnome.rhythmbox.plugins.vk', False)
		self.settings = Gio.Settings.new_full(schema, None, None)

		grid = Gtk.Grid()

		label = Gtk.Label("SECRET")
		label.set_alignment(0,0.5)
		secret_entry = Gtk.Entry()
		grid.attach(label, 0,0,1,1)
		grid.attach(secret_entry,1,0,1,1)

		label = Gtk.Label("USER_ID")
		label.set_alignment(0,0.5)
		user_id_entry = Gtk.Entry()
		grid.attach(label, 0,1,1,1)
		grid.attach(user_id_entry,1,1,1,1)

		label = Gtk.Label("API_ID")
		label.set_alignment(0,0.5)
		api_id_entry = Gtk.Entry()
		grid.attach(label, 0,2,1,1)
		grid.attach(api_id_entry,1,2,1,1)
		#initial fill from GSettings
		secret_entry.set_text(self.settings.get_string('secret'))
		user_id_entry.set_text(self.settings.get_string('user-id'))
		api_id_entry.set_text(self.settings.get_string('api-id'))
		#callback
		def commit_props(entry, event):
			self.settings.set_string('secret', secret_entry.get_text())
			self.settings.set_string('user-id', user_id_entry.get_text())
			self.settings.set_string('api-id', api_id_entry.get_text())
		#connecting to callback
		secret_entry.connect("focus-out-event", commit_props)
		user_id_entry.connect("focus-out-event", commit_props)
		api_id_entry.connect("focus-out-event", commit_props)

		return grid

