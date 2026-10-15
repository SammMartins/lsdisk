#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

for tool in python3 dpkg-deb find cp rm mkdir chmod; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf '[lsdisk] error: required tool not found: %s\n' "$tool" >&2
        exit 1
    fi
done

for input_file in pyproject.toml src/lsdisk; do
    if [[ ! -e "$input_file" ]]; then
        printf '[lsdisk] error: required input is missing: %s\n' "$input_file" >&2
        exit 1
    fi
done

# Read the version declared in pyproject.toml.
VERSION="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf '[lsdisk] error: invalid project version: %s\n' "$VERSION" >&2
    exit 1
fi

# If a GitHub Release tag is provided, validate it against the project version.
# Accepted examples: v0.1.1 and 0.1.1.
if [[ -n "${RELEASE_TAG:-}" ]]; then
    if [[ ! "$RELEASE_TAG" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ ||
        ( "$RELEASE_TAG" != "$VERSION" && "$RELEASE_TAG" != "v${VERSION}" ) ]]; then
        printf '[lsdisk] error: release tag and project version do not match.\n' >&2
        printf '[lsdisk] release tag: %s\n' "$RELEASE_TAG" >&2
        printf '[lsdisk] project version: %s\n' "$VERSION" >&2
        printf '[lsdisk] expected tag: %s or v%s\n' "$VERSION" "$VERSION" >&2
        exit 1
    fi

    echo "[lsdisk] Release tag validated: ${RELEASE_TAG}"
fi

PACKAGE="lsdisk"
ARCH="all"
BUILD_ROOT="${BUILD_ROOT:-$PROJECT_ROOT/build/deb}"
PKG_ROOT="$BUILD_ROOT/${PACKAGE}_${VERSION}_${ARCH}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/dist}"
OUTPUT_FILE="$OUTPUT_DIR/${PACKAGE}_${VERSION}_${ARCH}.deb"

echo "[lsdisk] Building Debian package..."
echo "[lsdisk] Version: ${VERSION}"

# Prepare build directories without removing unrelated artifacts.
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/DEBIAN"
mkdir -p "$PKG_ROOT/usr/lib/lsdisk"
mkdir -p "$PKG_ROOT/usr/bin"
mkdir -p "$OUTPUT_DIR"

# Copy Python source files.
cp -a src/lsdisk "$PKG_ROOT/usr/lib/lsdisk/"

# Keep the Debian-installed CLI versioned even though this package is not a wheel.
cat > "$PKG_ROOT/usr/lib/lsdisk/lsdisk/_version.py" <<EOF
"""Build-generated package version."""

__version__ = "${VERSION}"
EOF

# Remove Python bytecode and cache directories.
find "$PKG_ROOT/usr/lib/lsdisk" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$PKG_ROOT/usr/lib/lsdisk" -type f -name '*.pyc' -delete

# Create Debian package metadata.
cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: lsdisk
Version: ${VERSION}
Section: admin
Priority: optional
Architecture: all
Depends: python3 (>= 3.11), python3-rich (>= 13.0)
Maintainer: SammMartins <sammartins@users.noreply.github.com>
Description: Cross-distro Linux Storage Explorer
 A terminal utility to inspect Linux storage devices and
 display disk and partition usage information.
EOF

# Create the command-line executable.
cat > "$PKG_ROOT/usr/bin/lsdisk" <<'EOF'
#!/usr/bin/python3
import sys
from pathlib import Path

package_root = Path("/usr/lib/lsdisk")
if not (package_root / "lsdisk").is_dir():
    package_root = Path(__file__).resolve().parents[1] / "lib" / "lsdisk"
sys.path.insert(0, str(package_root))

from lsdisk.main import main

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod 755 "$PKG_ROOT/usr/bin/lsdisk"

# Build the Debian package.
dpkg-deb --build --root-owner-group "$PKG_ROOT" "$OUTPUT_FILE"

echo "[lsdisk] Package created successfully:"
echo "         $OUTPUT_FILE"
