#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${HOME}/.config/ytfzf"

mkdir -p "${BIN_DIR}" "${CONFIG_DIR}"

echo "Installing youtube-tui..."
ln -sfn "${REPO_DIR}/bin/youtube" "${BIN_DIR}/youtube"
ln -sfn "${REPO_DIR}/bin/mpv" "${BIN_DIR}/mpv"

if [[ ! -f "${CONFIG_DIR}/conf.sh" ]]; then
    cp -p "${REPO_DIR}/config/ytfzf/conf.sh" "${CONFIG_DIR}/conf.sh"
    echo "Created default config at ~/.config/ytfzf/conf.sh"
fi

echo "✔ Successfully installed youtube-tui to ${BIN_DIR}!"
