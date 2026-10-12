#!/usr/bin/env bash

set -Eeuo pipefail

# lsdisk Quick Installer
# Cross-distro Linux Storage Explorer

REPO="SammMartins/lsdisk"
BRANCH="${LSDISK_BRANCH:-master}"

INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lsdisk"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
VENV_DIR="$INSTALL_DIR/venv"

ARCHIVE_URL="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz"

log() {
    printf '[lsdisk] %s\n' "$1"
}

fail() {
    printf '[lsdisk] ERROR: %s\n' "$1" >&2
    exit 1
}

# Check required commands.
for command in curl tar python3; do
    command -v "$command" >/dev/null 2>&1 ||
        fail "Required command not found: $command"
done

# Do not run as root.
if [[ "$EUID" -eq 0 ]]; then
    fail "Run this installer as a regular user, without sudo."
fi

# Check Python version.
python3 -c \
    'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' ||
    fail "Python 3.10 or newer is required."

# Check virtual environment support.
python3 -c 'import venv' ||
    fail "Python venv support is missing."

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ARCHIVE="$TMP_DIR/lsdisk.tar.gz"
SOURCE_DIR="$TMP_DIR/source"

log "Downloading lsdisk from GitHub..."

curl --fail --silent --show-error --location \
    --retry 3 \
    "$ARCHIVE_URL" \
    --output "$ARCHIVE" ||
    fail "Download failed. Check the repository URL and branch."

mkdir -p "$SOURCE_DIR"

tar -xzf "$ARCHIVE" -C "$SOURCE_DIR" ||
    fail "Unable to extract the downloaded archive."

PROJECT_DIR="$(find "$SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d -print -quit)"

[[ -f "$PROJECT_DIR/pyproject.toml" ]] ||
    fail "pyproject.toml was not found."

log "Preparing installation directories..."

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# Create the virtual environment if necessary.
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    python3 -m venv "$VENV_DIR" ||
        fail "Unable to create the Python virtual environment."
fi

log "Installing lsdisk and its dependencies..."

"$VENV_DIR/bin/python" -m pip install \
    --disable-pip-version-check \
    "$PROJECT_DIR" ||
    fail "Installation failed. Check the Python dependencies."

[[ -x "$VENV_DIR/bin/lsdisk" ]] ||
    fail "Executable not found. Check the project entry points."

# Create the executable launcher.
cat > "$BIN_DIR/lsdisk" <<LAUNCHER
#!/usr/bin/env bash
exec "$VENV_DIR/bin/lsdisk" "\$@"
LAUNCHER

chmod +x "$BIN_DIR/lsdisk"

log "Installation completed successfully."
log "Executable: $BIN_DIR/lsdisk"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        log "Add the following directory to your PATH:"
        printf '  export PATH="%s:$PATH"\n' "$BIN_DIR"
        ;;
esac

log "Run 'lsdisk --help' to get started."
