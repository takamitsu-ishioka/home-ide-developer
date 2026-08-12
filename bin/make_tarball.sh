#!/bin/bash
# Tar+gzip a directory, excluding VCS/build artifacts and secret files.

if [ $# -lt 1 ]; then
  echo "Too few arguments"
  exit 1
fi

dir="$1"

tar \
  --exclude='*/.git' \
  --exclude='*/node_modules' \
  --exclude='*/bin' \
  --exclude='*/obj' \
  --exclude='*/dist' \
  --exclude='*/build' \
  --exclude='*.secret.env' \
  --exclude='.env' \
  --exclude='*.pem' \
  --exclude='*.p12' \
  --exclude='*.pfx' \
  --exclude='*credentials*' \
  -cvzf "$dir.tgz" "$dir"
