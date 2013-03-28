rhythmbox-vk
============

rhythmbox-3 plugin for vk.com

NOTES:

Working with rhythmbox-2.98

INSTALLATION:
cd ~/.local/share/rhythmbox/plugins
git clone https://github.com/radistmorse/rhythmbox-vk.git vk
edit ./vk/vk.py by providing
USER_ID=""
SECRET_KEY=""
API_ID=""
I really don't know how it should be obtained. I myself found it in similar
 scripts, but as it's kind of secret/personal I don't provide it. In the
 future I hope to make UI for it.

USAGE:
Plugin is currently in early development stage and doesn't work very good.
1. Enter the search line and press "Search"
2. IMPORTANT Wait until the database finished updating
3. IMPORTANT Press "search" again, thus updating metadata for found tracks. Fail
 to do so will result in polluted database.
4. Go to "library" and select the "vk.com" album. All the tracks will be there.

TODO:
1. Fix the track adding. The best would be to avoid adding tracks to the database
 at all. But if it will be proven to be unavoidable, it should be added properly
 in one go.
2. Make VKSource fully functional, turn it into the playlist and make it possible
 to delete tracks from it
3. Config + ability to download tracks


Based loosely on
https://github.com/ivalkeen/rhythmbox-vkontakte
Which in turn is based on
https://github.com/grunichev/rhythmbox-vkontakte




This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.


