    MP3 Auto Tagger - automatically tag your mp3 files
    Copyright (C) 2017  Alexander Tse

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# MP3-Auto-Tagger (v0.02?)
Incomplete, but kinda works (see below) <br>
Need to make it more configurable and user-friendly (and more intelligent)
## Usage
Move all the mp3 files you want to process into the directory "src/ready/" <br>
Then, make sure you have all the dependences installed, and run "python src/tagger.py" <br>
The program will automatically download tag info and 500x500 cover art (a .jpeg file) from the web <br>
and apply the new info to the mp3 files under "src/ready/" <br>
Lastly, the program will reposition your files to "src/processed" directory <br>
<br>
You should be able to find your files by the path <br>
"src/processed/\<artist>/\<year> - <album>/Disc \<disc#>/\<track#>. \<track title>.mp3"
<br>
## Note
Make sure that your files are partially tagged, this program right now cannot identify a track without looking at its current tags. So, missing both artists and album is no good. Missing both track number and track title grantees that the program will fail (doing its jobs). Otherwise, as long as they are reasonably tagged (by this, I meant that you can tell what songs they are by looking at the current tags), the program should pretty accurately determine what songs they are and help you complete the tagging.  <br>
<br>
Side Note: do not put duplicate songs to the "ready/", else one of them will have a wrong tag or not be tagged at all. <br>
Also, be sure to remove your songs from "processed/" folder once the process is done.
## Dependences
pip install mutagen <br>
pip install PIL <br>
pip install lxml <br>
pip install requests <br>
pip install discogs_client <br>
pip install py_stringmatching <br>
pip install munkres <br>
## Environment
Python 3.5+ should be fine (because that's mine's version) <br>
should work on Windows 10 machine


