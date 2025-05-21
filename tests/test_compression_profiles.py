#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for compression profiles functionality.

This script tests the compression profiles implementation to ensure that:
1. Profiles are correctly loaded and accessible
2. Profile settings are applied correctly to compression tasks
3. Media type detection works as expected
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from core.compression_profiles import CompressionProfileManager
from core.chdman import CHDTask, CHDTaskType


class TestCompressionProfiles(unittest.TestCase):
    """Test cases for compression profiles functionality."""

    def setUp(self):
        """Set up test environment."""
        self.profile_manager = CompressionProfileManager()

    def test_profile_loading(self):
        """Test that profiles are correctly loaded."""
        # Check that we have profiles for each media type
        self.assertIn('cd', self.profile_manager.profiles)
        self.assertIn('dvd', self.profile_manager.profiles)
        self.assertIn('hd', self.profile_manager.profiles)

        # Check that each media type has the expected profiles
        for media_type in ['cd', 'dvd', 'hd']:
            profiles = self.profile_manager.profiles[media_type]
            self.assertIn('optimal', profiles)
            self.assertIn('balanced', profiles)
            self.assertIn('fast', profiles)

    def test_cd_profiles(self):
        """Test CD-specific profiles."""
        cd_profiles = self.profile_manager.profiles['cd']

        # Test optimal profile
        optimal = cd_profiles['optimal']
        self.assertEqual(optimal.algorithms, 'cdlz,cdzl,cdfl')
        self.assertEqual(optimal.hunk_size, 9.8 * 1024)  # 9.8KB

        # Test balanced profile
        balanced = cd_profiles['balanced']
        self.assertEqual(balanced.algorithms, 'cdlz,cdzl')
        self.assertEqual(balanced.hunk_size, 9.8 * 1024)  # 9.8KB

        # Test fast profile
        fast = cd_profiles['fast']
        self.assertEqual(fast.algorithms, 'cdlz')
        self.assertEqual(fast.hunk_size, 9.8 * 1024)  # 9.8KB

    def test_dvd_profiles(self):
        """Test DVD-specific profiles."""
        dvd_profiles = self.profile_manager.profiles['dvd']

        # Test optimal profile
        optimal = dvd_profiles['optimal']
        self.assertEqual(optimal.algorithms, 'lzma')
        self.assertEqual(optimal.hunk_size, 2048)  # 2KB

        # Test balanced profile
        balanced = dvd_profiles['balanced']
        self.assertEqual(balanced.algorithms, 'zlib,huff')
        self.assertEqual(balanced.hunk_size, 2048)  # 2KB

        # Test fast profile
        fast = dvd_profiles['fast']
        self.assertEqual(fast.algorithms, 'zlib')
        self.assertEqual(fast.hunk_size, 2048)  # 2KB

    def test_hd_profiles(self):
        """Test HD-specific profiles."""
        hd_profiles = self.profile_manager.profiles['hd']

        # Test optimal profile
        optimal = hd_profiles['optimal']
        self.assertEqual(optimal.algorithms, 'lzma')
        self.assertEqual(optimal.hunk_size, 4096)  # 4KB

        # Test balanced profile
        balanced = hd_profiles['balanced']
        self.assertEqual(balanced.algorithms, 'zlib,huff')
        self.assertEqual(balanced.hunk_size, 4096)  # 4KB

        # Test fast profile
        fast = hd_profiles['fast']
        self.assertEqual(fast.algorithms, 'zlib')
        self.assertEqual(fast.hunk_size, 4096)  # 4KB

    def test_profile_application(self):
        """Test that profile settings are correctly applied to CHD tasks."""
        # Get a CD profile
        cd_profile = self.profile_manager.get_profile('cd', 'optimal')
        
        # Create a CHD task with profile settings
        task = CHDTask(
            task_type=CHDTaskType.CREATE,
            input_file='test.cue',
            output_file='test.chd',
            compression_level='best',
            hunk_size=cd_profile.hunk_size,
            algorithms=cd_profile.algorithms
        )
        
        # Verify task settings
        self.assertEqual(task.algorithms, 'cdlz,cdzl,cdfl')
        self.assertEqual(task.hunk_size, 9.8 * 1024)  # 9.8KB

    def test_media_type_detection(self):
        """Test media type detection based on file extension and size."""
        # Test CD detection by extension
        self.assertEqual(self.profile_manager.detect_media_type('test.cue'), 'cd')
        
        # Create a mock file size function for testing
        def mock_file_size(path):
            if path == 'small.iso':
                return 600 * 1024 * 1024  # 600MB (CD)
            elif path == 'large.iso':
                return 2 * 1024 * 1024 * 1024  # 2GB (DVD)
            elif path == 'huge.img':
                return 10 * 1024 * 1024 * 1024  # 10GB (HD)
            return 0
        
        # Test media type detection by size
        self.profile_manager._get_file_size = mock_file_size
        self.assertEqual(self.profile_manager.detect_media_type('small.iso'), 'cd')
        self.assertEqual(self.profile_manager.detect_media_type('large.iso'), 'dvd')
        self.assertEqual(self.profile_manager.detect_media_type('huge.img'), 'hd')


if __name__ == '__main__':
    unittest.main()
