#!/usr/bin/env bash
# Rend une scène en MP4. Usage : tools/rendre.sh SORTIE_DIR [--duree S]
set -euo pipefail
BLENDER="${BLENDER:-/home/claude/moteur3d/tools/blender-4.5.15-linux-x64/blender}"
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
exec "$BLENDER" -b --factory-startup --disable-autoexec -P "$RACINE/moteur/rendu.py" -- "$@"
