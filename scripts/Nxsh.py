from builder import *

class Nxsh(NightlyHomebrew):
    url = "https://github.com/Cesura/nxsh"

    pkg_files = {
        "nxsh.nro": "switch/nxsh/nxsh.nro",
        "nxsh.nsp": "atmosphere/titles/43000000000000ff/exefs.nsp"
    }

    title = "nxsh"
    author = "Cesura, friedkeenan"
    description = "BusyBox-like remote shell for the Nintendo Switch over telnet"
    category = "tool"
