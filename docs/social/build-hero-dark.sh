#!/usr/bin/env bash
# Render the 1200x630 dark cards in docs/social to 2400x1260 JPEGs:
#   h2kvm-hero-dark.html     -> h2kvm-hero-dark.jpg     (README hero and GitHub social preview)
#   migration-path-dark.html -> migration-path-dark.jpg (README suite section)
# Needs Google Chrome and macOS `sips`; nothing is installed.
#   ./docs/social/build-hero-dark.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
[[ -x "$CHROME" ]] || { echo "Google Chrome not found (set CHROME=...)" >&2; exit 1; }
TMP="$(mktemp -d "${TMPDIR:-/tmp}/hero.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
for name in h2kvm-hero-dark migration-path-dark; do
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=1200,630 --screenshot="$TMP/$name.png" "file://$HERE/$name.html" >/dev/null 2>&1
  sips -s format jpeg -s formatOptions 90 "$TMP/$name.png" --out "$HERE/$name.jpg" >/dev/null
  echo "wrote docs/social/$name.jpg"
done
