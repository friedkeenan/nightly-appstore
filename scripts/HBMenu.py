from builder import *

class HBMenu(NightlyHomebrew):
    pkg_files = {"nx-hbmenu.nro": "hbmenu.nro"}

    url = "https://github.com/switchbrew/nx-hbmenu"

    title = "Homebrew Menu"
    author = "yellows8, plutoo"
    category = "tool"
    description = "Run and load other Homebrew apps"
    details = "Homebrew Launcher for Switch!\\nPlaces hbmenu.nro on the root of your SD card.\\nSee https://switchbrew.org/wiki/Homebrew_Menu for more usage instructions.\\nAfter the exploit, HBL is launched by visiting the Album from the home menu."

    _make_args = "nx"