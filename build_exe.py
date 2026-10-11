"""
IRIS Executable Build Script
Automates PyInstaller standalone Windows executable generation.
"""

import sys
import subprocess
from pathlib import Path


def build():
    print("==================================================")
    print("   Building Standalone Executable for IRIS Assistant")
    print("==================================================")

    base_dir = Path(__file__).resolve().parent
    spec_file = base_dir / "iris.spec"

    if not spec_file.exists():
        print(f"[ERROR] Specification file not found: {spec_file}")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec_file)
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(base_dir))

    if result.returncode == 0:
        print("\n[SUCCESS] Build completed successfully!")
        dist_dir = base_dir / "dist" / "IRIS"
        print(f"Executable output directory: {dist_dir}")
        print(f"Launch with: {dist_dir / 'IRIS.exe'}")
    else:
        print(f"\n[ERROR] PyInstaller failed with exit code {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
