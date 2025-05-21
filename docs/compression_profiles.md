# RetroClamp Compression Profiles

## Overview

RetroClamp now includes media-specific compression profiles that optimize the compression process for different types of disk images. These profiles are designed to provide the best balance of compression ratio, speed, and compatibility based on the specific characteristics of each media type.

## Media Types

RetroClamp supports the following media types:

### CD Images

CD images (typically .cue/.bin or .iso files under 700MB) have specific sector sizes (2448 bytes) and benefit from specialized compression algorithms:

- **Optimal Profile**: Uses `cdlz,cdzl,cdfl` algorithms with 9.8KB hunk size (4 CD sectors)
- **Balanced Profile**: Uses `cdlz,cdzl` algorithms with 9.8KB hunk size
- **Fast Profile**: Uses `cdlz` algorithm with 9.8KB hunk size

### DVD Images

DVD images (typically .iso files over 700MB) have different characteristics:

- **Optimal Profile**: Uses `lzma` algorithm with 2KB hunk size (DVD sector size)
- **Balanced Profile**: Uses `zlib,huff` algorithms with 2KB hunk size
- **Fast Profile**: Uses `zlib` algorithm with 2KB hunk size

### Hard Disk Images

Hard disk images benefit from different settings:

- **Optimal Profile**: Uses `lzma` algorithm with 4KB hunk size (standard block size)
- **Balanced Profile**: Uses `zlib,huff` algorithms with 4KB hunk size
- **Fast Profile**: Uses `zlib` algorithm with 4KB hunk size

## Using Compression Profiles

1. Select a media type from the dropdown (or use Auto-detect)
2. Choose a compression profile from the dropdown
3. The profile description will show details about the selected profile
4. For advanced users, enable "Advanced Options" to manually configure compression algorithms and hunk sizes

## Technical Details

### CD-specific Algorithms

- `cdlz`: Specialized LZ77 variant optimized for CD data
- `cdzl`: Zlib compression optimized for CD data
- `cdfl`: FLAC-based compression for CD audio tracks

### General Algorithms

- `zlib`: Fast general-purpose compression
- `huff`: Huffman encoding, good for certain types of data
- `lzma`: High compression ratio but slower
- `zstd`: Newer algorithm with good balance of speed and compression (requires newer CHDMAN versions)

### Hunk Sizes

Hunk size is the amount of data processed at once during compression:

- CD images: Multiple of 2448 bytes (CD sector size)
- DVD images: 2048 bytes (DVD sector size)
- Hard disk images: 4096 bytes (standard block size)

Optimal hunk sizes improve both compression ratio and decompression performance.

## Automatic Media Detection

RetroClamp can automatically detect the media type based on:

1. File extension (.cue/.bin for CDs, .iso for DVDs/CDs)
2. File size (CDs < 700MB, DVDs > 700MB)

This detection helps select the appropriate compression profile automatically.
