# External Binaries

This directory contains external binaries used by RetroClamp.

## CHDMAN

CHDMAN is the CHD compression utility from the MAME project. It is used for compressing and decompressing disk images.

### Installation

1. Download the latest MAME release from https://www.mamedev.org/release.html
2. Extract the archive
3. Copy the `chdman.exe` file to this directory

Alternatively, you can build CHDMAN from source by following the instructions on the MAME website.

### Usage

RetroClamp will automatically detect and use the CHDMAN executable in this directory. If not found, it will attempt to find CHDMAN in the system PATH.
