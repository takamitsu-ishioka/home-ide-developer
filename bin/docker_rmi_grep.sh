#!/bin/bash
# Find Docker images matching a pattern and remove them after confirmation.
set -euo pipefail

log() { echo "$@" >&2; }

if [[ $# -lt 1 ]]; then
    echo "docker_rmi_grep.sh: Too few arguments" >&2
    echo "usage: docker_rmi_grep.sh <pattern> [--dry-run]" >&2
    echo "example: docker_rmi_grep.sh 'mmwave-.*:LOCAL'" >&2
    exit 1
fi

PATTERN=$1
DRY_RUN=false
if [[ ${2:-} == "--dry-run" ]]; then
    DRY_RUN=true
fi

mapfile -t IMAGES < <(docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "${PATTERN}" || true)

if [[ ${#IMAGES[@]} -eq 0 ]]; then
    log "No images matched: ${PATTERN}"
    exit 0
fi

log "Matched images:"
for img in "${IMAGES[@]}"; do
    log "  ${img}"
done

if "${DRY_RUN}"; then
    log "(dry-run: no images deleted)"
    exit 0
fi

log ""
read -r -p "Delete ${#IMAGES[@]} image(s)? [y/N] " confirm >&2
if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
    log "Aborted."
    exit 1
fi

for img in "${IMAGES[@]}"; do
    log ">>> Removing ${img} ..."
    docker rmi "${img}"
done

log ">>> Done."
