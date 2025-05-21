# RetroClamp Media-Specific Compression Profiles

## Overview

RetroClamp now features optimized compression profiles for different media types (CD, DVD, and hard disk images) as well as console-specific profiles for various gaming systems. These profiles are designed to provide the best balance of compression ratio, speed, and compatibility based on the specific characteristics of each media type and console requirements.

## How to Use Compression Profiles

1. **Select a Profile**: In the Compression tab, use the "Compression Profile" dropdown to select a profile that matches your media type.

2. **View Profile Details**: The profile description will update to show you the specific settings that will be applied.

3. **Automatic Detection**: RetroClamp can automatically detect the media type and console type based on file size, extension, and filename patterns, and suggest an appropriate profile.

4. **Console-Specific Optimization**: When RetroClamp detects a specific console type (e.g., PlayStation 1, Dreamcast), it will automatically apply the optimal compression settings for that console.

5. **Advanced Options**: For experienced users, you can still manually configure compression settings by enabling the "Advanced Options" checkbox.

## Available Profiles

### CD Images (e.g., .cue/.bin files, ISOs under 700MB)

- **CD - Optimal**: Best compression ratio for CD images using specialized CD algorithms
  - Algorithms: cdlz,cdzl,cdfl
  - Hunk Size: 9.8KB (4 CD sectors)

- **CD - Balanced**: Good balance of speed and compression for CD images
  - Algorithms: cdlz,cdzl
  - Hunk Size: 9.8KB

- **CD - Fast**: Fastest compression for CD images
  - Algorithm: cdlz
  - Hunk Size: 9.8KB

### DVD Images (e.g., ISOs over 700MB)

- **DVD - Optimal**: Best compression ratio for DVD images
  - Algorithm: lzma
  - Hunk Size: 2KB (DVD sector size)

- **DVD - Balanced**: Good balance of speed and compression for DVD images
  - Algorithms: zlib,huff
  - Hunk Size: 2KB

- **DVD - Fast**: Fastest compression for DVD images
  - Algorithm: zlib
  - Hunk Size: 2KB

### Hard Disk Images (e.g., .img, .hdd files)

- **HD - Optimal**: Best compression ratio for hard disk images
  - Algorithm: lzma
  - Hunk Size: 4KB (standard block size)

- **HD - Balanced**: Good balance of speed and compression for hard disk images
  - Algorithms: zlib,huff
  - Hunk Size: 4KB

- **HD - Fast**: Fastest compression for hard disk images
  - Algorithm: zlib
  - Hunk Size: 4KB

## Technical Details

### CD-specific Algorithms

- `cdlz`: Specialized LZ77 variant optimized for CD data
- `cdzl`: Zlib compression optimized for CD data
- `cdfl`: FLAC-based compression for CD audio tracks

### General Algorithms

- `zlib`: Fast general-purpose compression
- `huff`: Huffman encoding, good for certain types of data
- `lzma`: High compression ratio but slower

### Hunk Sizes

Hunk size is the amount of data processed at once during compression:

- CD images: Multiple of 2448 bytes (CD sector size)
- DVD images: 2048 bytes (DVD sector size)
- Hard disk images: 4096 bytes (standard block size)

Optimal hunk sizes improve both compression ratio and decompression performance.

## Console-Specific Profiles

RetroClamp now includes optimized profiles for specific gaming consoles. These profiles are automatically applied when RetroClamp detects a console-specific game image.

### CD-Based Consoles

- **PlayStation 1 Optimal**
  - Optimized for PlayStation 1 CD images
  - Algorithms: cdlz,cdzl,cdfl
  - Hunk Size: 9.4KB (4 CD sectors)

- **SEGA CD/Mega CD Optimal**
  - Optimized for SEGA CD/Mega CD images
  - Algorithms: cdlz,cdzl,cdfl
  - Hunk Size: 9.4KB (4 CD sectors)

- **SEGA Saturn Optimal**
  - Optimized for SEGA Saturn CD images
  - Algorithms: cdlz,cdzl,cdfl
  - Hunk Size: 9.4KB (4 CD sectors)

- **TurboGrafx-CD/PC Engine CD Optimal**
  - Optimized for TurboGrafx-CD/PC Engine CD images
  - Algorithms: cdlz,cdzl,cdfl
  - Hunk Size: 9.4KB (4 CD sectors)

- **Dreamcast Optimal**
  - Optimized for Dreamcast GD-ROM images
  - Algorithms: cdlz,cdzl,cdfl
  - Hunk Size: 18.8KB (8 CD sectors, Dreamcast specific)

### DVD-Based Consoles

- **PlayStation 2 Optimal**
  - Optimized for PlayStation 2 DVD images
  - Algorithm: lzma
  - Hunk Size: 2KB (DVD sector size)

- **PSP Optimal**
  - Optimized for PSP UMD images
  - Algorithm: lzma
  - Hunk Size: 2KB (UMD sector size)

## Benefits of Using Media-Specific Profiles

1. **Better Compression Ratios**: By using algorithms optimized for specific media types, you can achieve better compression ratios.

2. **Faster Compression**: The profiles are designed to balance speed and compression based on media characteristics.

3. **Improved Compatibility**: The profiles ensure that the compressed CHD files will work correctly with emulators and other tools.

4. **Simplified Workflow**: No need to manually configure complex compression settings - just select the appropriate profile for your media type.

5. **Console-Optimized Settings**: Automatically apply the best settings for specific gaming consoles to ensure maximum compatibility with emulators.
