#!/bin/bash
# Remount the G: drive (drvfs) at /mnt/g.
set -euo pipefail

sudo mount -t drvfs G: /mnt/g
echo "/mnt/g remounted." >&2
ls /mnt/g
