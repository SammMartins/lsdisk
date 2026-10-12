#!/usr/bin/env bash

set -Eeuo pipefail

APP_NAME="lsdisk"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lsdisk"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
LAUNCHER="$BIN_DIR/$APP_NAME"

log() {
    printf '[lsdisk] %s\n' "$1"
}

fail() {
    printf '[lsdisk] ERROR: %s\n' "$1" >&2
    exit 1
}

if [[ "$EUID" -eq 0 ]]; then
    fail "Run the uninstaller as a regular user, without sudo."
fi

if [[ ! -d "$INSTALL_DIR" && ! -f "$LAUNCHER" ]]; then
    log "No installation found."
    exit 0
fi

log "Removing lsdisk installation..."

if [[ -e "$LAUNCHER" || -L "$LAUNCHER" ]]; then
    rm -- "$LAUNCHER"
fi

if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf -- "$INSTALL_DIR"
fi

log "Uninstallation completed."
log "Project source files were not modified."
