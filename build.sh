#!/usr/bin/env bash
# build.sh — Build a self-contained MoneyTracker binary for Linux.
#
# Usage:
#   ./build.sh
#
# Output:
#   dist/moneytracker/                 — the installable directory
#   moneytracker-linux-<arch>.tar.gz   — release archive for GitHub

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Locate PyInstaller (prefer the project venv) ──────────────────────────────
if [ -f ".venv/bin/pyinstaller" ]; then
    PYINSTALLER=".venv/bin/pyinstaller"
elif command -v pyinstaller &>/dev/null; then
    PYINSTALLER="pyinstaller"
else
    echo "ERROR: pyinstaller not found. Install it with:"
    echo "  pip install pyinstaller"
    exit 1
fi

echo "==> Using PyInstaller: $PYINSTALLER"

# ── Clean previous build artefacts ───────────────────────────────────────────
echo "==> Cleaning previous build..."
rm -rf build/ dist/

# ── Run PyInstaller ───────────────────────────────────────────────────────────
echo "==> Running PyInstaller..."
"$PYINSTALLER" moneytracker.spec

echo ""
echo "==> Build complete!"
echo "    Executable : dist/moneytracker/moneytracker"
echo "    Bundle dir : dist/moneytracker/"

# ── Create release tarball ────────────────────────────────────────────────────
ARCH="$(uname -m)"   # e.g. x86_64, aarch64
TARBALL="moneytracker-linux-${ARCH}.tar.gz"

echo ""
echo "==> Creating release tarball: ${TARBALL}..."
tar -czf "${TARBALL}" -C dist moneytracker

echo "==> Done!"
echo ""
echo "────────────────────────────────────────────────────────────"
echo " Release archive : ${TARBALL}"
echo " Upload this file to your GitHub Release."
echo "────────────────────────────────────────────────────────────"
echo ""
echo " User installation:"
echo "   tar -xzf ${TARBALL} -C ~/.local/"
echo "   sudo ln -s ~/.local/moneytracker/moneytracker /usr/local/bin/moneytracker"
echo "   moneytracker --terminal"
echo "────────────────────────────────────────────────────────────"
