#!/usr/bin/env python3
"""
ZIP File Diagnostic Tool
Run this separately to diagnose issues with specific ZIP files
"""

import os
import shutil
import tempfile
import traceback
import zipfile


def diagnose_zip_file(zip_path):
    """Comprehensive ZIP file diagnosis"""
    print(f"🔍 Diagnosing ZIP file: {zip_path}")
    print("=" * 60)

    # Basic file checks
    if not os.path.exists(zip_path):
        print("❌ File does not exist")
        return False

    file_size = os.path.getsize(zip_path)
    print(f"📁 File size: {file_size:,} bytes")

    if file_size == 0:
        print("❌ File is empty")
        return False

    # Check file header
    try:
        with open(zip_path, "rb") as f:
            header = f.read(10)
        print(f"🔢 File header: {header}")
        if header[:2] != b"PK":
            print("❌ Invalid ZIP signature")
            return False
        else:
            print("✅ Valid ZIP signature")
    except Exception as e:
        print(f"❌ Error reading file header: {e}")
        return False

    # Try to open with zipfile
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            print("✅ ZIP file opens successfully")

            # Check integrity
            bad_file = zf.testzip()
            if bad_file:
                print(f"❌ ZIP integrity check failed. Bad file: {bad_file}")
                return False
            else:
                print("✅ ZIP integrity check passed")

            # List contents
            file_list = zf.namelist()
            print(f"📦 Contains {len(file_list)} files")

            if len(file_list) == 0:
                print("⚠️  ZIP is empty")
            else:
                print("📄 First 10 files:")
                for i, filename in enumerate(file_list[:10]):
                    info = zf.getinfo(filename)
                    password_protected = "🔒" if (info.flag_bits & 0x1) else "🔓"
                    print(
                        f"   {i + 1:2d}. {password_protected} {filename} ({info.file_size:,} bytes)"
                    )

                if len(file_list) > 10:
                    print(f"   ... and {len(file_list) - 10} more files")

            # Check for password protection
            encrypted_files = [f for f in file_list if zf.getinfo(f).flag_bits & 0x1]
            if encrypted_files:
                print(f"🔒 {len(encrypted_files)} files are password protected")
            else:
                print("🔓 No password protection detected")

    except zipfile.BadZipFile as e:
        print(f"❌ Bad ZIP file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error opening ZIP: {e}")
        return False

    # Test extraction
    print("\n🚀 Testing extraction...")
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="zip_test_")
        print(f"📁 Temp directory: {temp_dir}")

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        extracted_items = os.listdir(temp_dir)
        print(f"✅ Extraction successful! {len(extracted_items)} items extracted")

        if len(extracted_items) > 0:
            print("📄 Extracted items:")
            for item in extracted_items[:10]:
                item_path = os.path.join(temp_dir, item)
                if os.path.isdir(item_path):
                    print(f"   📁 {item}/")
                else:
                    size = os.path.getsize(item_path)
                    print(f"   📄 {item} ({size:,} bytes)")

        return True

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        print(f"🔍 Full traceback:\n{traceback.format_exc()}")
        return False
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("🧹 Cleaned up temp directory")


def main():
    """Test with a specific file"""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python zip_diagnostic.py <path_to_zip_file>")
        sys.exit(1)

    zip_path = sys.argv[1]
    success = diagnose_zip_file(zip_path)

    print("\n" + "=" * 60)
    if success:
        print("✅ DIAGNOSIS COMPLETE - ZIP file appears to be working")
    else:
        print("❌ DIAGNOSIS COMPLETE - ZIP file has issues")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
