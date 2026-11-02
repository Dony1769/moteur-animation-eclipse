#!/usr/bin/env bash
# Rend la scène de 4 s. Usage : tools/rendre_4s.sh SORTIE [--image N] [--samples S] [--res LxH]
set -euo pipefail
BLENDER="${BLENDER:-/home/claude/moteur3d/tools/blender-4.5.15-linux-x64/blender}"
export BLENDER_USER_SCRIPTS="${BLENDER_USER_SCRIPTS:-/home/claude/moteur3d/scripts}"
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
exec "$BLENDER" -b --factory-startup --disable-autoexec -P "$RACINE/moteur/rendu4s.py" -- "$@"
