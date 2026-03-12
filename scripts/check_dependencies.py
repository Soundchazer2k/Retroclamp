"""
Script to check and print extraction dependencies required for RetroClamp.
Run this to debug missing libraries or tools.
"""

import importlib.util
import platform
import shutil


def check_extraction_dependencies():
    deps = {
        "py7zr": importlib.util.find_spec("py7zr") is not None,
        "libarchive": importlib.util.find_spec("libarchive") is not None,
        "7z_cli": shutil.which("7z") is not None
        or shutil.which("7za") is not None
        or shutil.which("p7zip") is not None,
    }
    system = platform.system().lower()
    print(f"[DEPENDENCY CHECK] Platform: {system}")
    for dep, available in deps.items():
        print(f"  {dep}: {'OK' if available else 'MISSING'}")
    missing = [k for k, v in deps.items() if not v]
    if missing:
        print(
            f"[DEPENDENCY WARNING] Missing: {', '.join(missing)}. Extraction for some formats may fail."
        )
    else:
        print("[DEPENDENCY CHECK] All required dependencies are available.")


if __name__ == "__main__":
    check_extraction_dependencies()
