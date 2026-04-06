#!/bin/bash
set -euo pipefail
# Gemini CLI を直接使ってツイート生成・投稿を行う
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 が見つかりません。Python 3 をインストールしてください。" >&2
    exit 1
fi
SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_SOURCE" ]; do
    SCRIPT_SOURCE="$(readlink "$SCRIPT_SOURCE")"
    [[ "$SCRIPT_SOURCE" = /* ]] || SCRIPT_SOURCE="$(dirname "${BASH_SOURCE[0]}")/$SCRIPT_SOURCE"
done
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
exec python3 "$SCRIPT_DIR/tweet_gen.py" "$@"
