#!/bin/bash
# Wrapper around find(1) that also prunes names listed in .findignore.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "$0")"
FINDIGNORE="${SCRIPT_DIR}/.findignore"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "usage: ${SCRIPT_NAME} [find-arguments...]" >&2
    echo "example: ${SCRIPT_NAME} . -name '*.py'" >&2
    echo "example: ${SCRIPT_NAME}" >&2
    echo "note: names listed in ${FINDIGNORE} are pruned (dir contents and the entry itself excluded)" >&2
    exit 0
fi

# Split leading path arguments from the find expression: find requires all
# paths before the expression, and expression tokens start with -, ( or !.
paths=()
i=0
args=("$@")
while [[ $i -lt ${#args[@]} ]]; do
    case "${args[$i]}" in
        -*|'('|'!') break ;;
        *) paths+=("${args[$i]}") ;;
    esac
    i=$((i + 1))
done
expr=("${args[@]:$i}")

# If the caller's expression has no action of its own, add -print so that
# behavior matches plain find(1) when no pruning is configured, and so the
# pruned-branch below doesn't fall back to find's implicit whole-expression
# -print (which would still print the pruned entry itself).
has_action=false
for tok in "${expr[@]:-}"; do
    case "$tok" in
        -print|-print0|-fprint|-fprint0|-fprintf|-printf|-exec|-execdir|-ok|-okdir|-delete|-ls|-fls)
            has_action=true
            break
            ;;
    esac
done
if ! "$has_action"; then
    expr+=(-print)
fi

prune_terms=()
if [[ -f "$FINDIGNORE" ]]; then
    while IFS= read -r pattern || [[ -n "$pattern" ]]; do
        [[ -z "$pattern" || "$pattern" == \#* ]] && continue
        if [[ ${#prune_terms[@]} -gt 0 ]]; then
            prune_terms+=(-o)
        fi
        prune_terms+=(-name "$pattern")
    done < "$FINDIGNORE"
fi

if [[ ${#prune_terms[@]} -gt 0 ]]; then
    find "${paths[@]}" \( "${prune_terms[@]}" \) -prune -o \( "${expr[@]}" \)
else
    find "${paths[@]}" "${expr[@]}"
fi
