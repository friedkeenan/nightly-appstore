from builder import *

class Hekate(NightlyHomebrew):
    url = "https://github.com/CTCaer/hekate"

    category = "tool"
    description = "A custom bootloader for the Nintendo Switch"

    pkg_files = {
        "output/hekate.bin": "bootloader/update.bin",
        "output/nyx.bin": "bootloader/sys/nyx.bin",
        "output/libsys_lp0.bso": "bootloader/sys/libsys_lp0.bso",
        "output/libsys_minerva.bso": "bootloader/sys/libsys_minerva.bso",
        "res/patches.ini": "bootloader/patches_template.ini",
        "nyx/resources": "bootloader/res"
    }
