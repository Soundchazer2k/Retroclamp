"""Compression profiles for RetroClamp.

This module provides predefined compression profiles for different media types,
optimizing compression settings based on the specific characteristics of
CD, DVD, and hard disk images, as well as specific gaming consoles.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class CompressionProfile:
    """Compression profile for a specific media type.
    
    This class defines the optimal compression settings for a specific media type,
    including algorithm selection, hunk size, and other parameters.
    """
    name: str
    media_type: str  # 'CD', 'DVD', or 'Hard Disk'
    algorithms: str  # Comma-separated list of algorithms
    hunk_size: int   # Hunk size in bytes
    description: str
    
    def __str__(self):
        return f"{self.name} ({self.description})"


class CompressionProfileManager:
    """Manager for compression profiles.
    
    This class provides access to predefined compression profiles for
    different media types and allows for custom profile creation.
    """
    
    def __init__(self):
        """Initialize the CompressionProfileManager."""
        self._profiles = self._create_default_profiles()
    
    def _create_default_profiles(self) -> Dict[str, CompressionProfile]:
        """Create default compression profiles.
        
        Returns:
            Dictionary of profile_id -> CompressionProfile
        """
        profiles = {}
        
        # CD profiles
        profiles['cd_optimal'] = CompressionProfile(
            name="CD Optimal",
            media_type="CD",
            algorithms="cdlz,cdzl,cdfl",  # CD-specific algorithms in optimal order
            hunk_size=4 * 2448,  # 9792 bytes (4 CD sectors)
            description="Best compression ratio for CD images"
        )
        
        profiles['cd_balanced'] = CompressionProfile(
            name="CD Balanced",
            media_type="CD",
            algorithms="cdlz,cdzl",  # CD-specific algorithms, balanced
            hunk_size=4 * 2448,  # 9792 bytes (4 CD sectors)
            description="Good balance of speed and compression for CD images"
        )
        
        profiles['cd_fast'] = CompressionProfile(
            name="CD Fast",
            media_type="CD",
            algorithms="cdlz",  # Fastest CD-specific algorithm
            hunk_size=4 * 2448,  # 9792 bytes (4 CD sectors)
            description="Fastest compression for CD images"
        )
        
        # DVD profiles
        profiles['dvd_optimal'] = CompressionProfile(
            name="DVD Optimal",
            media_type="DVD",
            algorithms="lzma",  # Best compression for DVD
            hunk_size=2048,  # 2KB (DVD sector size)
            description="Best compression ratio for DVD images"
        )
        
        profiles['dvd_balanced'] = CompressionProfile(
            name="DVD Balanced",
            media_type="DVD",
            algorithms="zlib,huff",  # Good balance for DVD
            hunk_size=2048,  # 2KB (DVD sector size)
            description="Good balance of speed and compression for DVD images"
        )
        
        profiles['dvd_fast'] = CompressionProfile(
            name="DVD Fast",
            media_type="DVD",
            algorithms="zlib",  # Fastest algorithm for DVD
            hunk_size=2048,  # 2KB (DVD sector size)
            description="Fastest compression for DVD images"
        )
        
        # Hard Disk profiles
        profiles['hd_optimal'] = CompressionProfile(
            name="Hard Disk Optimal",
            media_type="Hard Disk",
            algorithms="lzma",  # Best compression for HD
            hunk_size=4096,  # 4KB (standard block size)
            description="Best compression ratio for hard disk images"
        )
        
        profiles['hd_balanced'] = CompressionProfile(
            name="Hard Disk Balanced",
            media_type="Hard Disk",
            algorithms="zlib,huff",  # Good balance for HD
            hunk_size=4096,  # 4KB (standard block size)
            description="Good balance of speed and compression for hard disk images"
        )
        
        profiles['hd_fast'] = CompressionProfile(
            name="Hard Disk Fast",
            media_type="Hard Disk",
            algorithms="zlib",  # Fastest algorithm for HD
            hunk_size=4096,  # 4KB (standard block size)
            description="Fastest compression for hard disk images"
        )
        
        # Special profiles for newer CHDMAN versions
        profiles['zstd_balanced'] = CompressionProfile(
            name="ZSTD Balanced",
            media_type="Any",
            algorithms="zstd",  # ZSTD algorithm (newer CHDMAN versions)
            hunk_size=4096,  # 4KB (works well for most media types)
            description="Balanced compression using ZSTD algorithm (newer CHDMAN versions)"
        )
        
        return profiles
    
    def get_profile(self, profile_id: str) -> Optional[CompressionProfile]:
        """Get a compression profile by ID.
        
        Args:
            profile_id: ID of the profile to retrieve
            
        Returns:
            CompressionProfile or None if not found
        """
        return self._profiles.get(profile_id)
    
    def get_profile_for_media_type(self, media_type: str, level: str = 'normal') -> Optional[CompressionProfile]:
        """Get a compression profile for a specific media type and compression level.
        
        Args:
            media_type: Media type ('CD', 'DVD', or 'Hard Disk')
            level: Compression level ('best', 'normal', 'fast', or 'none')
            
        Returns:
            CompressionProfile or None if not found
        """
        # Normalize inputs
        media_type = media_type.lower()
        level = level.lower()
        
        # Map compression level to profile suffix
        if level == 'best':
            suffix = 'optimal'
        elif level == 'normal':
            suffix = 'balanced'
        elif level == 'fast':
            suffix = 'fast'
        else:  # none or unknown
            return None
            
        # Construct profile ID
        if media_type == 'cd':
            profile_id = f'cd_{suffix}'
        elif media_type == 'dvd':
            profile_id = f'dvd_{suffix}'
        elif media_type in ['hard disk', 'hd']:
            profile_id = f'hd_{suffix}'
        else:
            # Default to ZSTD for unknown media types if available
            return self.get_profile('zstd_balanced')
        
        return self.get_profile(profile_id)
    
    def get_all_profiles(self) -> List[CompressionProfile]:
        """Get all available compression profiles.
        
        Returns:
            List of all CompressionProfile objects
        """
        return list(self._profiles.values())
    
    def get_profiles_for_media_type(self, media_type: str) -> List[CompressionProfile]:
        """Get all profiles for a specific media type.
        
        Args:
            media_type: Media type ('CD', 'DVD', or 'Hard Disk')
            
        Returns:
            List of CompressionProfile objects for the specified media type
        """
        media_type = media_type.lower()
        return [p for p in self._profiles.values() if p.media_type.lower() == media_type]
        
    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes or 0 if file not found
        """
        try:
            return os.path.getsize(file_path)
        except (OSError, FileNotFoundError):
            return 0
            
    def detect_media_type(self, file_path: str) -> str:
        """Detect media type based on file extension and size.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Media type (cd, dvd, hd)
        """
        # Check by extension first
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".cue", ".bin", ".iso"]:
            # For .iso files, check size to determine if it's a CD or DVD
            if ext == ".iso":
                file_size = self._get_file_size(file_path)
                if file_size < 700 * 1024 * 1024:  # Less than 700MB is likely a CD
                    return "cd"
                else:  # Larger than 700MB is likely a DVD
                    return "dvd"
            # .cue and .bin files are typically CD images
            return "cd"
        elif ext in [".img", ".hdd"]:
            # .img and .hdd files are typically hard disk images
            return "hd"
        elif ext in [".gdi"]:  # Dreamcast uses .gdi files
            return "cd"  # Dreamcast uses CD-based media
        
        # If extension doesn't give a clear answer, check file size
        file_size = self._get_file_size(file_path)
        if file_size < 700 * 1024 * 1024:  # Less than 700MB is likely a CD
            return "cd"
        elif file_size < 5 * 1024 * 1024 * 1024:  # Less than 5GB is likely a DVD
            return "dvd"
        else:  # Larger than 5GB is likely a hard disk
            return "hd"
            
    def detect_console_type(self, file_path: str) -> str:
        """Detect console type based on file extension and size.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Console type or empty string if unknown
        """
        # Check by extension first
        filename = os.path.basename(file_path).lower()
        ext = os.path.splitext(file_path)[1].lower()
        
        # Dreamcast uses .gdi files
        if ext == ".gdi":
            return "dreamcast"
            
        # Check for PSP games (typically .iso files between 300MB and 1.8GB)
        if ext == ".iso" or ext == ".cso":
            file_size = self._get_file_size(file_path)
            if 300 * 1024 * 1024 <= file_size <= 1.8 * 1024 * 1024 * 1024:
                # Check if filename contains PSP indicators
                if "psp" in filename:
                    return "psp"
                    
        # Check for PS2 games (typically .iso files larger than 700MB)
        if ext == ".iso":
            file_size = self._get_file_size(file_path)
            if file_size > 700 * 1024 * 1024:
                # Check if filename contains PS2 indicators
                if "ps2" in filename:
                    return "ps2"
                    
        # Check for PS1 games (typically .bin/.cue files)
        if ext == ".bin" or ext == ".cue" or (ext == ".iso" and self._get_file_size(file_path) < 700 * 1024 * 1024):
            # Check if filename contains PS1 indicators
            if "ps1" in filename or "psx" in filename:
                return "ps1"
                
        # Check for SEGA CD games
        if ext == ".bin" or ext == ".cue":
            # Check if filename contains SEGA CD indicators
            if "segacd" in filename or "sega-cd" in filename or "mega-cd" in filename:
                return "sega_cd"
                
        # Check for SEGA Saturn games
        if ext == ".bin" or ext == ".cue":
            # Check if filename contains Saturn indicators
            if "saturn" in filename:
                return "saturn"
                
        # Check for TurboGrafx-CD / PC Engine CD games
        if ext == ".bin" or ext == ".cue":
            # Check if filename contains TurboGrafx-CD indicators
            if "tgcd" in filename or "turbografx" in filename or "pcengine" in filename:
                return "tg_cd"
                
        # If we couldn't determine the console type, return empty string
        return ""
        
    def get_console_profile(self, console_type: str) -> Optional[CompressionProfile]:
        """Get the recommended compression profile for a specific console.
        
        Args:
            console_type: Console type (e.g., 'ps1', 'ps2', 'dreamcast')
            
        Returns:
            CompressionProfile object for the specified console or None if not found
        """
        console_profiles = {
            # CD-based consoles
            "ps1": CompressionProfile(
                id="ps1_optimal",
                name="PlayStation 1 Optimal",
                description="Optimized for PlayStation 1 CD images",
                media_type="cd",
                compression_level="best",
                compression_algorithm="cdlz,cdzl,cdfl",
                hunk_size=2352 * 4  # 4 CD sectors
            ),
            "sega_cd": CompressionProfile(
                id="sega_cd_optimal",
                name="SEGA CD Optimal",
                description="Optimized for SEGA CD/Mega CD images",
                media_type="cd",
                compression_level="best",
                compression_algorithm="cdlz,cdzl,cdfl",
                hunk_size=2352 * 4  # 4 CD sectors
            ),
            "saturn": CompressionProfile(
                id="saturn_optimal",
                name="SEGA Saturn Optimal",
                description="Optimized for SEGA Saturn CD images",
                media_type="cd",
                compression_level="best",
                compression_algorithm="cdlz,cdzl,cdfl",
                hunk_size=2352 * 4  # 4 CD sectors
            ),
            "tg_cd": CompressionProfile(
                id="tg_cd_optimal",
                name="TurboGrafx-CD Optimal",
                description="Optimized for TurboGrafx-CD/PC Engine CD images",
                media_type="cd",
                compression_level="best",
                compression_algorithm="cdlz,cdzl,cdfl",
                hunk_size=2352 * 4  # 4 CD sectors
            ),
            "dreamcast": CompressionProfile(
                id="dreamcast_optimal",
                name="Dreamcast Optimal",
                description="Optimized for Dreamcast GD-ROM images",
                media_type="cd",
                compression_level="best",
                compression_algorithm="cdlz,cdzl,cdfl",
                hunk_size=2352 * 8  # 8 CD sectors (Dreamcast specific)
            ),
            
            # DVD-based consoles
            "ps2": CompressionProfile(
                id="ps2_optimal",
                name="PlayStation 2 Optimal",
                description="Optimized for PlayStation 2 DVD images",
                media_type="dvd",
                compression_level="best",
                compression_algorithm="lzma",
                hunk_size=2048  # DVD sector size
            ),
            "psp": CompressionProfile(
                id="psp_optimal",
                name="PSP Optimal",
                description="Optimized for PSP UMD images",
                media_type="dvd",
                compression_level="best",
                compression_algorithm="lzma",
                hunk_size=2048  # UMD sector size
            ),
        }
        
        return console_profiles.get(console_type.lower())
        
    def recommend_profile(self, file_path: str) -> Optional[CompressionProfile]:
        """Recommend the optimal compression profile based on file analysis.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Recommended CompressionProfile or None if no recommendation
        """
        # First try to detect console type
        console_type = self.detect_console_type(file_path)
        if console_type:
            # If we detected a console, return its optimized profile
            console_profile = self.get_console_profile(console_type)
            if console_profile:
                return console_profile
        
        # If no console detected or no profile for that console,
        # fall back to media type detection
        media_type = self.detect_media_type(file_path)
        
        # Return the best compression profile for the detected media type
        if media_type == "cd":
            return self.get_profile("cd_best")
        elif media_type == "dvd":
            return self.get_profile("dvd_best")
        elif media_type == "hd":
            return self.get_profile("hd_best")
        
        # If all else fails, return None
        return None
