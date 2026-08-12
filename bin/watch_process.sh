#!/bin/bash

_script_name=$(basename "$0")

function usage() {
    cat << _MESSAGE >&2
$_script_name: $*
Usage: $_script_name <process_name>
Example: $_script_name claude
_MESSAGE
    exit 1
}

if [ $# -eq 0 ]; then
    usage "No process name provided."
elif [ $# -gt 1 ]; then
    usage "Too many arguments provided."
fi

process_name="$1"

pid=($(pgrep -x "$process_name"))

if [ ${#pid[@]} -eq 0 ]; then
    usage "No process found with name: $process_name"
elif [ ${#pid[@]} -gt 1 ]; then
    ps -o pid,ppid,%cpu,%mem,rss,vsz,etime,time,stat,cmd -p "${pid[@]}" >&2
    usage "Multiple processes found with name: $process_name. Please specify a more specific name."
fi

top -p "${pid[@]}"
