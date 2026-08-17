#!/bin/bash
# exec claude
# -c: resume the most recent session in this directory automatically
# --remote-control home-ide-developer: enable remote control, session named after this repo
# always starts at home-ide-developer repo root

cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1
exec claude -c --remote-control home-ide-developer
