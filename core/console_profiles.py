#!/usr/bin/env python3

"""
Console-specific compression profiles for RetroClamp.

This module defines optimized compression profiles for various gaming consoles,
based on their specific media types and emulator recommendations.
"""

from typing import Any, Dict, List, Optional

from .compression_profiles import CompressionProfile


class ConsoleProfile(CompressionProfile):
    """Console-specific compression profile."""

    def __init__(
        self,
        name: str,
        description: str,
        algorithms: str,
        hunk_size: int,
        console: str,
        emulators: List[str],
        command: str,
    ):
        """Initialize a console-specific compression profile.

        Args:
            name: Profile name
            description: Profile description
            algorithms: Compression algorithms to use
            hunk_size: Hunk size in bytes
            console: Console name
            emulators: List of compatible emulators
            command: CHDMAN command to use (createcd, createdvd, etc.)
        """
        super().__init__(name, description, algorithms, hunk_size)  # type: ignore
        self.console = console
        self.emulators = emulators
        self.command = command

    def get_info(self) -> Dict[str, Any]:
        """Get profile information.

        Returns:
            Dictionary with profile information
        """
        return {
            "name": self.name,
            "description": self.description,
            "algorithms": self.algorithms,
            "hunk_size": self.hunk_size,
            "console": self.console,
            "emulators": self.emulators,
            "command": self.command,
        }


class ConsoleProfileManager:
    """Manager for console-specific compression profiles."""

    def __init__(self):
        """Initialize the console profile manager."""
        self.profiles = self._create_profiles()

    def _create_profiles(self) -> Dict[str, Dict[str, ConsoleProfile]]:
        """Create console-specific compression profiles.

        Returns:
            Dictionary of profiles by console
        """
        profiles = {}

        # CD-based consoles (SEGA CD, PS1, TurboGrafx-CD, Saturn)
        cd_consoles: Dict[str, Dict[str, Any]] = {
            "sega_cd": {
                "name": "SEGA CD / Mega CD",
                "emulators": ["RetroArch", "MAME", "Kega Fusion"],
            },
            "ps1": {
                "name": "PlayStation 1",
                "emulators": ["RetroArch", "DuckStation", "Mednafen"],
            },
            "tg_cd": {
                "name": "TurboGrafx-CD / PC Engine CD",
                "emulators": ["RetroArch", "Mednafen", "MAME"],
            },
            "saturn": {
                "name": "SEGA Saturn",
                "emulators": ["RetroArch", "Mednafen", "MAME"],
            },
        }

        # Create profiles for CD-based consoles
        for console_id, console_info in cd_consoles.items():
            profiles[console_id] = {
                "optimal": ConsoleProfile(
                    name=f"{console_info['name']} - Optimal",
                    description=f"Best compression for {console_info['name']} games",
                    algorithms="cdlz,cdzl,cdfl",
                    hunk_size=18816,  # 8 CD sectors (standard for these consoles)
                    console=console_info["name"],
                    emulators=console_info["emulators"],
                    command="createcd",
                ),
                "balanced": ConsoleProfile(
                    name=f"{console_info['name']} - Balanced",
                    description=f"Good balance for {console_info['name']} games",
                    algorithms="cdlz,cdzl",
                    hunk_size=18816,  # 8 CD sectors
                    console=console_info["name"],
                    emulators=console_info["emulators"],
                    command="createcd",
                ),
                "fast": ConsoleProfile(
                    name=f"{console_info['name']} - Fast",
                    description=f"Fastest compression for {console_info['name']} games",
                    algorithms="cdlz",
                    hunk_size=18816,  # 8 CD sectors
                    console=console_info["name"],
                    emulators=console_info["emulators"],
                    command="createcd",
                ),
            }

        # Dreamcast (uses GDI files)
        profiles["dreamcast"] = {
            "optimal": ConsoleProfile(
                name="Dreamcast - Optimal",
                description="Best compression for Dreamcast games",
                algorithms="cdlz,cdzl,cdfl",
                hunk_size=18816,  # 8 CD sectors
                console="SEGA Dreamcast",
                emulators=["RetroArch", "Redream", "Flycast"],
                command="createcd",
            ),
            "balanced": ConsoleProfile(
                name="Dreamcast - Balanced",
                description="Good balance for Dreamcast games",
                algorithms="cdlz,cdzl",
                hunk_size=18816,  # 8 CD sectors
                console="SEGA Dreamcast",
                emulators=["RetroArch", "Redream", "Flycast"],
                command="createcd",
            ),
            "fast": ConsoleProfile(
                name="Dreamcast - Fast",
                description="Fastest compression for Dreamcast games",
                algorithms="cdlz",
                hunk_size=18816,  # 8 CD sectors
                console="SEGA Dreamcast",
                emulators=["RetroArch", "Redream", "Flycast"],
                command="createcd",
            ),
        }

        # PlayStation 2 (DVD-based)
        profiles["ps2"] = {
            "optimal": ConsoleProfile(
                name="PlayStation 2 - Optimal",
                description="Best compression for PS2 games",
                algorithms="lzma",
                hunk_size=4096,  # 2 DVD sectors
                console="PlayStation 2",
                emulators=["PCSX2", "RetroArch"],
                command="createdvd",
            ),
            "balanced": ConsoleProfile(
                name="PlayStation 2 - Balanced",
                description="Good balance for PS2 games",
                algorithms="zlib,huff",
                hunk_size=4096,  # 2 DVD sectors
                console="PlayStation 2",
                emulators=["PCSX2", "RetroArch"],
                command="createdvd",
            ),
            "fast": ConsoleProfile(
                name="PlayStation 2 - Fast",
                description="Fastest compression for PS2 games",
                algorithms="zlib",
                hunk_size=4096,  # 2 DVD sectors
                console="PlayStation 2",
                emulators=["PCSX2", "RetroArch"],
                command="createdvd",
            ),
        }

        # PlayStation Portable (PSP)
        profiles["psp"] = {
            "optimal": ConsoleProfile(
                name="PSP - Optimal",
                description="Best compression for PSP games (recommended for PPSSPP)",
                algorithms="lzma",
                hunk_size=2048,  # Recommended for PPSSPP
                console="PlayStation Portable",
                emulators=["PPSSPP", "RetroArch"],
                command="createdvd",
            ),
            "balanced": ConsoleProfile(
                name="PSP - Balanced",
                description="Good balance for PSP games",
                algorithms="zlib,huff",
                hunk_size=2048,  # Recommended for PPSSPP
                console="PlayStation Portable",
                emulators=["PPSSPP", "RetroArch"],
                command="createdvd",
            ),
            "fast": ConsoleProfile(
                name="PSP - Fast",
                description="Fastest compression for PSP games",
                algorithms="zlib",
                hunk_size=2048,  # Recommended for PPSSPP
                console="PlayStation Portable",
                emulators=["PPSSPP", "RetroArch"],
                command="createdvd",
            ),
        }

        return profiles

    def get_profile(
        self, console: str, profile_type: str = "balanced"
    ) -> Optional[ConsoleProfile]:
        """Get a profile for a specific console.

        Args:
            console: Console ID
            profile_type: Profile type (optimal, balanced, fast)

        Returns:
            ConsoleProfile or None if not found
        """
        if console in self.profiles and profile_type in self.profiles[console]:
            profile = self.profiles[console][profile_type]
            if isinstance(profile, ConsoleProfile):
                return profile
        return None

    def get_consoles(self) -> list:
        """Get list of available consoles.

        Returns:
            List of console IDs
        """
        return list(self.profiles.keys())

    def get_console_name(self, console_id: str) -> str:
        """Get the full name of a console from its ID.

        Args:
            console_id: Console ID

        Returns:
            Console name or empty string if not found
        """
        if console_id in self.profiles:
            # Get the name from any profile (they all have the same console name)
            profile = next(iter(self.profiles[console_id].values()))
            if isinstance(profile, ConsoleProfile):
                return profile.console
        return ""

    def get_profile_types(self, console: str) -> list:
        """Get available profile types for a console.

        Args:
            console: Console ID

        Returns:
            List of profile types
        """
        if console in self.profiles:
            return list(self.profiles[console].keys())
        return []
