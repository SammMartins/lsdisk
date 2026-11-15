#!/usr/bin/env bash

set -Eeuo pipefail

# lsdisk Quick Installer
# Cross-distro Linux Storage Explorer

PROJECT_NAME="lsdisk"
VERSION="${LSDISK_VERSION:-0.1.3}"
PYPI_API_URL="https://pypi.org/pypi/${PROJECT_NAME}/${VERSION}/json"

INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lsdisk"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
VENV_DIR="$INSTALL_DIR/venv"

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
    'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' ||
    fail "Python 3.11 or newer is required."

# Check virtual environment support.
python3 -c 'import venv' ||
    fail "Python venv support is missing."

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    fail "LSDISK_VERSION must be an exact published version such as 0.1.3."
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

rollback_replacement() {
    local rollback_failed=0

    set +e
    if [[ "$new_launcher" -eq 1 ]]; then
        rm -f -- "$LAUNCHER" || rollback_failed=1
    fi
    if [[ "$new_installation" -eq 1 ]]; then
        rm -rf -- "$INSTALL_DIR" || rollback_failed=1
    fi
    if [[ "$previous_launcher" -eq 1 ]]; then
        mv -- "$LAUNCHER_BACKUP" "$LAUNCHER" || rollback_failed=1
    fi
    if [[ "$previous_installation" -eq 1 ]]; then
        mv -- "$INSTALL_BACKUP" "$INSTALL_DIR" || rollback_failed=1
    fi
    set -e

    if [[ "$rollback_failed" -eq 1 ]]; then
        printf '[lsdisk] ERROR: Installation failed and automatic rollback was incomplete.\n' >&2
    else
        printf '[lsdisk] Previous installation and launcher were restored.\n' >&2
    fi
}

on_exit() {
    local status=$?
    if [[ "$replacement_active" -eq 1 && "$replacement_succeeded" -eq 0 ]]; then
        rollback_replacement
    fi
    rm -rf -- "$TMP_DIR"
    exit "$status"
}

trap on_exit EXIT

METADATA="$TMP_DIR/pypi.json"
ARTIFACT_INFO="$TMP_DIR/artifact.info"
ARCHIVE="$TMP_DIR/lsdisk.tar.gz"
SOURCE_DIR="$TMP_DIR/source"
STAGING_INSTALL_DIR="$TMP_DIR/install"
STAGING_VENV_DIR="$STAGING_INSTALL_DIR/venv"
LAUNCHER="$BIN_DIR/$PROJECT_NAME"

replacement_active=0
replacement_succeeded=0
previous_installation=0
previous_launcher=0
new_installation=0
new_launcher=0
INSTALL_BACKUP=""
LAUNCHER_BACKUP=""

log "Resolving lsdisk ${VERSION} from PyPI..."

curl --fail --silent --show-error --location \
    --retry 3 \
    "$PYPI_API_URL" \
    --output "$METADATA" ||
    fail "Unable to retrieve PyPI metadata for lsdisk ${VERSION}."

if ! python3 - "$METADATA" "$VERSION" "$ARTIFACT_INFO" <<'PY'
from collections.abc import Mapping
import json
import re
import sys
from urllib.parse import urlparse

metadata_path, version, output_path = sys.argv[1:]
try:
    metadata = json.loads(open(metadata_path, encoding="utf-8").read())
    if not isinstance(metadata, Mapping):
        raise ValueError("metadata is not an object")

    info = metadata.get("info")
    if not isinstance(info, Mapping):
        raise ValueError("metadata info is not an object")
    if info.get("version") != version:
        raise ValueError("version mismatch")

    urls = metadata.get("urls")
    if not isinstance(urls, list):
        raise ValueError("metadata urls is not a list")

    for item in urls:
        if not isinstance(item, Mapping):
            raise ValueError("metadata URL entry is not an object")
        for key in ("packagetype", "filename", "url"):
            if key in item and not isinstance(item[key], str):
                raise ValueError(f"metadata {key} is not a string")
        digests = item.get("digests")
        if digests is not None and not isinstance(digests, Mapping):
            raise ValueError("metadata digests is not an object")
        if isinstance(digests, Mapping) and (
            "sha256" in digests and not isinstance(digests["sha256"], str)
        ):
            raise ValueError("metadata sha256 is not a string")

    expected_name = f"lsdisk-{version}.tar.gz"
    matches = [
        item for item in metadata.get("urls", [])
        if item.get("packagetype") == "sdist"
        and item.get("filename") == expected_name
    ]
    if len(matches) != 1:
        raise ValueError("source distribution not found")
    artifact = matches[0]
    digests = artifact.get("digests")
    digest = digests.get("sha256") if isinstance(digests, Mapping) else None
    url = artifact.get("url")
    if not isinstance(digest, str) or not isinstance(url, str):
        raise ValueError("source distribution metadata is incomplete")
    parsed = urlparse(url or "")
    if (
        not re.fullmatch(r"[0-9a-f]{64}", digest or "")
        or parsed.scheme != "https"
        or parsed.netloc != "files.pythonhosted.org"
    ):
        raise ValueError("invalid artifact metadata")
except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
    raise SystemExit(1)
except (AttributeError, KeyError):
    raise SystemExit(1)

with open(output_path, "w", encoding="ascii") as output:
    output.write(f"{url}\n{digest}\n")
PY
then
    fail "The requested lsdisk version or source artifact is unavailable."
fi

read -r ARCHIVE_URL < "$ARTIFACT_INFO"
read -r EXPECTED_SHA256 < <(sed -n '2p' "$ARTIFACT_INFO")

log "Downloading and verifying lsdisk ${VERSION}..."

curl --fail --silent --show-error --location \
    --retry 3 \
    "$ARCHIVE_URL" \
    --output "$ARCHIVE" ||
    fail "Download failed for lsdisk ${VERSION}."

if ! python3 - "$ARCHIVE" "$EXPECTED_SHA256" <<'PY'
import hashlib
import hmac
import sys

archive_path, expected = sys.argv[1:]
digest = hashlib.sha256()
with open(archive_path, "rb") as archive:
    for chunk in iter(lambda: archive.read(1024 * 1024), b""):
        digest.update(chunk)
if not hmac.compare_digest(digest.hexdigest(), expected):
    raise SystemExit(1)
PY
then
    fail "SHA-256 verification failed; the downloaded artifact was rejected."
fi

mkdir -p "$SOURCE_DIR"

if ! python3 - "$ARCHIVE" "$SOURCE_DIR" <<'PY'
from pathlib import Path, PurePosixPath
import sys
import tarfile

archive_path, destination = sys.argv[1:]
root = Path(destination).resolve()

try:
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = {}
        for member in archive.getmembers():
            name = member.name
            path = PurePosixPath(name)
            if (
                not name
                or path.is_absolute()
                or any(part == ".." for part in path.parts)
            ):
                raise ValueError(f"unsafe archive member path: {name!r}")

            normalized = str(PurePosixPath(*path.parts))
            if normalized in ("", "."):
                raise ValueError(f"invalid archive member path: {name!r}")
            if normalized in members:
                raise ValueError(
                    f"duplicate archive member path: {name!r}"
                )

            if not (member.isdir() or member.isfile()):
                raise ValueError(f"unsupported archive member type: {name!r}")

            members[normalized] = member.isdir()

            target = (root / normalized).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"archive member escapes extraction directory: {name!r}")

        for normalized in members:
            path = PurePosixPath(normalized)
            for parent in path.parents:
                parent_name = str(parent)
                if parent_name in members and not members[parent_name]:
                    raise ValueError(
                        f"archive member is a file parent: {normalized!r}"
                    )
except (OSError, UnicodeError, ValueError, tarfile.TarError) as exc:
    print(f"invalid source archive: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
then
    fail "The source archive contains unsafe or unsupported members."
fi

tar -xzf "$ARCHIVE" -C "$SOURCE_DIR" ||
    fail "Unable to extract the verified source distribution."

PROJECT_DIR="$(find "$SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d -print -quit)"

[[ -n "$PROJECT_DIR" && -f "$PROJECT_DIR/pyproject.toml" ]] ||
    fail "pyproject.toml was not found."

log "Preparing the isolated installation..."

python3 -m venv "$STAGING_VENV_DIR" ||
    fail "Unable to create the Python virtual environment."

# Ensure pip is available inside the virtual environment.
"$STAGING_VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1 ||
    fail "pip is missing from the virtual environment. Install Python venv/pip support for your distribution."

log "Installing lsdisk and its dependencies..."

"$STAGING_VENV_DIR/bin/python" -m pip install \
    --disable-pip-version-check \
    --upgrade \
    "$PROJECT_DIR" ||
    fail "Installation failed. Check the Python dependencies."

[[ -x "$STAGING_VENV_DIR/bin/lsdisk" ]] ||
    fail "Executable not found. Check the project entry points."

mkdir -p "$(dirname "$INSTALL_DIR")" "$BIN_DIR"

cat > "$TMP_DIR/lsdisk-launcher" <<LAUNCHER
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" -m lsdisk.main "\$@"
LAUNCHER
chmod +x "$TMP_DIR/lsdisk-launcher"

LAUNCHER_BACKUP="$(mktemp "${LAUNCHER}.backup.XXXXXX")"
rm -f -- "$LAUNCHER_BACKUP"
INSTALL_BACKUP="$(mktemp -d "${INSTALL_DIR}.backup.XXXXXX")"
rmdir -- "$INSTALL_BACKUP"

replacement_active=1

if [[ -d "$INSTALL_DIR" || -f "$INSTALL_DIR" || -L "$INSTALL_DIR" ]]; then
    mv -- "$INSTALL_DIR" "$INSTALL_BACKUP"
    previous_installation=1
fi

mv -- "$STAGING_INSTALL_DIR" "$INSTALL_DIR"
new_installation=1

if [[ "${LSDISK_TEST_FAIL_AFTER_INSTALL_REPLACEMENT:-0}" == "1" ]]; then
    fail "Simulated failure after application replacement."
fi

if [[ -e "$LAUNCHER" || -L "$LAUNCHER" ]]; then
    mv -- "$LAUNCHER" "$LAUNCHER_BACKUP"
    previous_launcher=1
fi

mv -- "$TMP_DIR/lsdisk-launcher" "$LAUNCHER"
new_launcher=1

if [[ "${LSDISK_TEST_FAIL_DURING_LAUNCHER_REPLACEMENT:-0}" == "1" ]]; then
    fail "Simulated failure during launcher replacement."
fi

replacement_succeeded=1
if ! rm -rf -- "$INSTALL_BACKUP" "$LAUNCHER_BACKUP"; then
    log "Installation completed, but obsolete backup cleanup failed."
fi

log "Installation completed successfully."
log "Version: $VERSION"
log "Executable: $BIN_DIR/lsdisk"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        log "Add the following directory to your PATH:"
        printf '  export PATH="%s:$PATH"\n' "$BIN_DIR"
        ;;
esac

log "Run 'lsdisk --help' to get started."
