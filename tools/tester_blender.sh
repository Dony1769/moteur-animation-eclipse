#!/usr/bin/env bash
# Lance un test qui a besoin de Blender. Usage : tools/tester_blender.sh tests/fichier.py
set -uo pipefail
BLENDER="${BLENDER:-/home/claude/moteur3d/tools/blender-4.5.15-linux-x64/blender}"
export BLENDER_USER_SCRIPTS="${BLENDER_USER_SCRIPTS:-/home/claude/moteur3d/scripts}"
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
SORTIE="$("$BLENDER" -b --factory-startup --disable-autoexec -P "$RACINE/$1" 2>&1)"
if grep -q "_OK" <<<"$SORTIE" && ! grep -q "Traceback\|AssertionError" <<<"$SORTIE"; then
  echo "OK"
else
  echo "$SORTIE" | tail -20
  echo "ÉCHEC"; exit 1
fi
