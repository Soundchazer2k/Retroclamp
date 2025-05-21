# **CHDMAN Usage and Emulators Supporting CHD Files**

This document outlines which emulated consoles commonly utilize the CHD (Compressed Hunks of Data) file format for game content and provides the typical CHDMAN commands used for conversion. It also lists emulators that frequently support or prefer the CHD format.

## **Emulated Consoles Commonly Using CHD Files**

The following emulated consoles are known to frequently use CHD files as their default or preferred format for storing game content, particularly for CD-based games:

* **SEGA CD / Mega CD:** This was one of the earlier consoles to benefit from the CHD format for its CD-ROM games. The default hunk size used by CHDMAN for the createcd command is 18,816 bytes (8 sectors).1  
  chdman createcd \-i \<path\_to\_cue\_file\>.cue \-o \<desired\_chd\_name\>.chd

  * createcd: Specifies the operation for creating a CHD from CD-ROM image files.  
  * \-i \<path\_to\_cue\_file\>.cue: Indicates the input file, which is typically the .cue file that describes the CD image layout.  
  * \-o \<desired\_chd\_name\>.chd: Defines the desired name and extension for the output CHD file.  
* **Sony PlayStation 1 (PS1):** CHD is a popular format for PS1 games, helping to compress their often large CD images. The default hunk size for createcd is also 18,816 bytes.1  
  chdman createcd \-i \<path\_to\_cue\_file\>.cue \-o \<desired\_chd\_name\>.chd

  * Parameters are the same as for SEGA CD.  
* **NEC TurboGrafx-CD / PC Engine CD:** This console's CD-ROM library also benefits from the lossless compression offered by the CHD format. The default hunk size for createcd is 18,816 bytes.1  
  chdman createcd \-i \<path\_to\_cue\_file\>.cue \-o \<desired\_chd\_name\>.chd

  * Parameters are the same as for SEGA CD.  
* **SEGA Saturn:** Similar to other CD-based consoles from the era, the Saturn's game library is often stored in CHD format for emulation. The default hunk size for createcd is 18,816 bytes.1  
  chdman createcd \-i \<path\_to\_cue\_file\>.cue \-o \<desired\_chd\_name\>.chd

  * Parameters are the same as for SEGA CD.  
* **SEGA Dreamcast:** Dreamcast games, which are typically stored as .gdi files, are also commonly converted to CHD for more efficient storage. The default hunk size for createcd is 18,816 bytes.1  
  chdman createcd \-i \<path\_to\_gdi\_file\>.gdi \-o \<desired\_chd\_name\>.chd

  * createcd: Still the operation for CD-based images.  
  * \-i \<path\_to\_gdi\_file\>.gdi: Specifies the input file as the .gdi file.2  
  * \-o \<desired\_chd\_name\>.chd: Defines the output CHD file name.  
* **Sony PlayStation 2 (PS2):** While .iso files are common, CHD format, especially created with the createdvd command, is increasingly used for PS2 games for better compatibility with some emulators. The default hunk size for createdvd is 4096 bytes (2 sectors).1  
  chdman createdvd \-i \<path\_to\_iso\_file\>.iso \-o \<desired\_chd\_name\>.chd

  * createdvd: Specifies the operation for creating a CHD from DVD image files.1  
  * \-i \<path\_to\_iso\_file\>.iso: Indicates the input file as the .iso file.2  
  * \-o \<desired\_chd\_name\>.chd: Defines the output CHD file name.  
* **Sony PlayStation Portable (PSP):** CHD format, created using the createdvd command, is supported by PSP emulators. The default hunk size for createdvd is 4096 bytes.1 However, it is often recommended to use a hunk size of 2048 for better performance with emulators like PPSSPP.4  
  chdman createdvd \-i \<path\_to\_iso\_or\_cso\_file\> \-o \<desired\_chd\_name\>.chd \-hs 2048

  * createdvd: Operation for DVD-like images.1  
  * \-i \<path\_to\_iso\_or\_cso\_file\>: Input file, can be .iso or .cso.5  
  * \-o \<desired\_chd\_name\>.chd: Output CHD file name.  
  * \-hs 2048: Sets the hunk size to 2048 bytes, which is recommended for PPSSPP for potentially better performance.4

## **Emulators Commonly Supporting CHD Files**

Many modern emulators support the CHD format due to its advantages in compression and single-file management. Some emulators that frequently support or prefer CHD files include:

* **MAME (Multiple Arcade Machine Emulator):** CHD was originally developed for MAME to handle the hard drive and CD-ROM data of arcade machines.  
* **RetroArch:** This popular multi-system emulator frontend supports CHD files for various cores, including those for SEGA CD, PlayStation 1, SEGA Saturn, Dreamcast, and more.  
* **DuckStation:** A PlayStation 1 emulator that supports CHD format.4  
* **PCSX2:** A PlayStation 2 emulator that has added improved support for CHD files, often created using the createdvd command.7  
* **PPSSPP:** A PlayStation Portable emulator that supports CHD format, with recommendations to use the createdvd command and a hunk size of 2048\.4  
* **Redream:** A Dreamcast emulator that supports CHD files.4  
* **Flycast:** Another Dreamcast emulator that supports CHD format.4  
* **Mednafen:** A multi-system emulator that supports CHD for systems like PlayStation 1 and SEGA Saturn.4  
* **Standalone Emulators:** Many individual console emulators (e.g., for specific PlayStation 1 or SEGA Saturn emulators) also support the CHD format.  
* **Emulation Frontends:** Frontends like LaunchBox and RetroPie often have built-in support or configurations that work well with CHD files.4

It's always a good idea to consult the documentation of your specific emulator to confirm its preferred file formats and any specific recommendations for using CHD files, including optimal hunk sizes for performance.

#### **Works cited**

1. chdman – CHD (Compressed Hunks of Data) File Manager \- MAME Documentation, accessed May 10, 2025, [https://docs.mamedev.org/tools/chdman.html](https://docs.mamedev.org/tools/chdman.html)  
2. The Ultimate ROM File Compression Guide \- Retro Game Corps, accessed May 10, 2025, [https://retrogamecorps.com/2023/02/06/the-ultimate-rom-file-compression-guide/](https://retrogamecorps.com/2023/02/06/the-ultimate-rom-file-compression-guide/)  
3. PPSSPP warns about bad performant CHD while using ZSTD · Issue \#18925 \- GitHub, accessed May 10, 2025, [https://github.com/hrydgard/ppsspp/issues/18925](https://github.com/hrydgard/ppsspp/issues/18925)  
4. Single batch file with Menu to run multiple chdman operations \- Emulation \- LaunchBox Community Forums, accessed May 10, 2025, [https://forums.launchbox-app.com/topic/77440-mame-chdman-single-batch-file-with-menu-to-run-multiple-chdman-operations/](https://forums.launchbox-app.com/topic/77440-mame-chdman-single-batch-file-with-menu-to-run-multiple-chdman-operations/)  
5. Reconverting CHD files for use with PPSSPP (guide) : r/SBCGaming \- Reddit, accessed May 10, 2025, [https://www.reddit.com/r/SBCGaming/comments/1ayn09s/reconverting\_chd\_files\_for\_use\_with\_ppsspp\_guide/](https://www.reddit.com/r/SBCGaming/comments/1ayn09s/reconverting_chd_files_for_use_with_ppsspp_guide/)  
6. Tips for converting ISO to CHD (PPSSPP) : r/PPSSPPemulator \- Reddit, accessed May 10, 2025, [https://www.reddit.com/r/PPSSPPemulator/comments/1faq23t/tips\_for\_converting\_iso\_to\_chd\_ppsspp/](https://www.reddit.com/r/PPSSPPemulator/comments/1faq23t/tips_for_converting_iso_to_chd_ppsspp/)  
7. PCSX2 now supports the CHD format : r/emulation \- Reddit, accessed May 10, 2025, [https://www.reddit.com/r/emulation/comments/mbcmgn/pcsx2\_now\_supports\_the\_chd\_format/](https://www.reddit.com/r/emulation/comments/mbcmgn/pcsx2_now_supports_the_chd_format/)  
8. Curious about sega cd size \- Off-Topic \- Libretro Forums, accessed May 10, 2025, [https://forums.libretro.com/t/curious-about-sega-cd-size/34180](https://forums.libretro.com/t/curious-about-sega-cd-size/34180)