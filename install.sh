#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${HOME}/.config/ytfzf"

mkdir -p "${BIN_DIR}" "${CONFIG_DIR}"

echo "Installing youtube-tui..."

# Verify required dependencies
MISSING=()
for dep in python3 mpv yt-dlp chafa wl-copy micro; do
    if ! command -v "$dep" >/dev/null 2>&1; then
        MISSING+=("$dep")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "⚠ Warning: The following recommended dependencies were not found in PATH: ${MISSING[*]}"
    echo "  Install them on Arch via: sudo pacman -S ${MISSING[*]}"
fi

ln -sfn "${REPO_DIR}/bin/youtube" "${BIN_DIR}/youtube"
ln -sfn "${REPO_DIR}/bin/mpv" "${BIN_DIR}/mpv"

if [[ ! -f "${CONFIG_DIR}/conf.sh" ]]; then
    cp -p "${REPO_DIR}/config/ytfzf/conf.sh" "${CONFIG_DIR}/conf.sh"
    echo "Created default config at ~/.config/ytfzf/conf.sh"
fi

echo "✔ Successfully installed youtube-tui to ${BIN_DIR}!"
