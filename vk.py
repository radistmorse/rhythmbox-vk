from gi.repository import RB, Gtk, GdkPixbuf, GObject, Peas
import rb #"Loader" heler class
from xml.dom import minidom #xml parser
import urllib2 #search line escaping
import hashlib #search line hashing
from html_decode import decode_htmlentities #results decoding

import gettext
gettext.install('rhythmbox', RB.locale_dir())

USER_ID=""
SECRET_KEY=""
API_ID=""

class VKRhythmbox(GObject.Object, Peas.Activatable):
	__gtype_name = 'VKRhythmboxPlugin'
	object = GObject.property(type=GObject.GObject)

	def __init__(self):
		GObject.Object.__init__(self)
			
	def do_activate(self):
		print "activating vk plugin"

		what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
		icon = GdkPixbuf.Pixbuf.new_from_file_at_size(self.plugin_info.get_data_dir()+"/vk.png", width, height)

		shell = self.object
		db = shell.props.db
		model = RB.RhythmDBQueryModel.new_empty(db)
		self.source = GObject.new (VKSource, shell=shell, name=_("VK Playlist"), query_model=model, pixbuf=icon)
		self.source.setup(db)

		group = RB.DisplayPageGroup.get_by_id ("library")
		shell.append_display_page(self.source, group)

	def do_deactivate(self):
		print "deactivating vk plugin"
		self.source.delete_thyself()
		self.source = None

class VKSource(RB.Source):
	def __init__(self, **kwargs):
		super(VKSource, self).__init__(kwargs)

	def setup(self, db):
		shell = self.props.shell
		self.db = db
		source_container = Gtk.VBox()
		search_line = Gtk.HBox()
		search_input = Gtk.Entry()
		search_line.pack_start(search_input, expand=True, fill=True, padding=5)
		search_button = Gtk.Button(_("Search"))
		search_line.pack_start(search_button, expand=False, fill=False, padding=5)
		search_amount_label = Gtk.Label(_("Number of results"))
		search_line.pack_start(search_amount_label, expand=False, fill=False, padding=5)
		search_amount = Gtk.Entry()
		search_line.pack_start(search_amount, expand=False, fill=False, padding=5)
		search_amount.set_text("100")
		source_container.pack_start(search_line, expand=False, fill=False, padding=0)
		source_container.show_all()

		search_button.connect("clicked", self.search_button_clicked, search_input, search_amount)

		songs = RB.EntryView(db=db, shell_player=shell.props.shell_player, is_drag_source=False, is_drag_dest=False)
		songs.append_column(RB.EntryViewColumn.TITLE, True)
		songs.append_column(RB.EntryViewColumn.ARTIST, True)
		songs.append_column(RB.EntryViewColumn.DURATION, True)

		songs.set_model(self.props.query_model)
		songs.show_all()
		source_container.pack_start(songs, expand=True, fill=True, padding=0)

		self.pack_start(source_container, expand=True, fill=True, padding=0)

	def search_button_clicked(self, button, s_input, s_amount) :
		search_line = s_input.get_text()
		search_num = s_amount.get_text()
		try :
			search_num = str(int(search_num))
		except :
			search_num = "100"
		# Only do anything if there is text in the search entry
		if len(search_line) > 0 :
			search = VkontakteSearch(search_line, search_num, self.db, self.props.query_model)
			search.start()

GObject.type_register(VKSource)

class XMLResult:
	def __init__(self, entry):
		# Store the function. This will be called when we are ready to be added to the db.
		self.title = entry.getElementsByTagName('title')[0].firstChild.nodeValue.strip()
		self.duration = int(entry.getElementsByTagName('duration')[0].firstChild.nodeValue)
		self.artist = entry.getElementsByTagName('artist')[0].firstChild.nodeValue.strip()
		self.url = entry.getElementsByTagName('url')[0].firstChild.nodeValue

class VkontakteSearch:
	def __init__(self, search_line, search_num, db, query_model):
		self.search_line = search_line
		self.search_num = search_num
		self.db = db
		self.query_model = query_model
		self.entries_hashes = []
	
	def make_sig(self, method, query, amount):
		str = "%sapi_id=%scount=%smethod=%sq=%stest_mode=1v=2.0%s" % (USER_ID, API_ID, amount, method, query, SECRET_KEY)
		return hashlib.md5(str).hexdigest()
		
	def is_complete(self):
		return self.search_complete
	
	def add_entry(self, result):
		entry = self.db.entry_lookup_by_location(result.url)
		if entry is not None :
			if result.title:
				self.db.entry_set(entry, RB.RhythmDBPropType.TITLE, decode_htmlentities(result.title).encode("utf-8"))
			if result.duration:
				self.db.entry_set(entry, RB.RhythmDBPropType.DURATION, result.duration)
			if result.artist:
				self.db.entry_set(entry, RB.RhythmDBPropType.ARTIST, decode_htmlentities(result.artist).encode("utf-8"))

			self.db.entry_set(entry, RB.RhythmDBPropType.ALBUM, "vk.com".encode("utf-8"))
		if entry is not None :
			self.query_model.add_entry(entry, -1)

	def add_uri(self, result) :
		strhash = ('%s%s%s' % (result.title, result.artist, result.duration)).lower()
		if strhash in self.entries_hashes:
			return

		# add only distinct songs (unique by title+artist+duration) to prevent duplicates
		self.entries_hashes.append(strhash)

		entry = self.db.entry_lookup_by_location(result.url)
		if entry is None :
			self.db.add_uri(result.url)

	def on_search_results_recieved(self, data):


		data = data.decode("utf-8")
		# vkontakte sometimes returns invalid XML with empty first line
		data = data.lstrip()
		# remove invalid symbol that occured in titles/artist
		data = data.replace(u'\uffff', '')
		xmldoc = minidom.parseString(data.encode("utf-8"))
		audios = xmldoc.getElementsByTagName("audio")
		xmlresults = []
		for audio in audios:
			rez = XMLResult(audio)
			self.add_uri(rez)
			xmlresults.append(rez)
		self.db.commit()
		# here we should wait for sync
		for rez in xmlresults:
			self.add_entry(rez)
		self.db.commit()

	# Starts searching
	def start(self):
		sig = self.make_sig('audio.search', self.search_line, self.search_num)
		path = "http://api.vk.com/api.php?api_id=%s&count=%s&v=2.0&method=audio.search&sig=%s&test_mode=1&q=%s" % (API_ID, self.search_num, sig, urllib2.quote(self.search_line))
		loader = rb.Loader()
		loader.get_url(path, self.on_search_results_recieved)

