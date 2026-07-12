#!/usr/bin/env bash
# watch_pid.sh — poll until a pid is dead OR a zombie, then exit 0.
#
# Usage: watch_pid.sh <pid> [interval_seconds]
#
# Why a shared helper: `kill -0 <pid>` SUCCEEDS on a zombie (a process that has
# exited but not yet been reaped), so a naive `while kill -0` watcher hangs
# forever on a finished-but-unreaped job. This bit the project TWICE — the
# Task-18 gotcha (kill -0 succeeds on zombies) and again during the 2026-07-12
# c2 touch, whose process ended as a zombie and the pid-watcher missed it.
# This helper treats a Z-state process as dead: it polls `ps -o stat=` and stops
# when the pid is gone OR its state begins with Z.
#
# On completion it prints: `pid <pid> finished (state: <last-state>)` and exits 0.

set -u

pid="${1:-}"
interval="${2:-5}"

if [ -z "${pid}" ]; then
	echo "usage: watch_pid.sh <pid> [interval_seconds]" >&2
	exit 2
fi

if ! [ "${pid}" -gt 0 ] 2>/dev/null; then
	echo "watch_pid.sh: pid must be a positive integer, got '${pid}'" >&2
	exit 2
fi

last_state="(gone)"
while true; do
	# `ps -o stat=` prints only the state field (no header). Empty output means
	# the pid is gone. A leading Z means a zombie — treat as dead.
	state="$(ps -o stat= -p "${pid}" 2>/dev/null | awk 'NR==1{print $1}')"
	if [ -z "${state}" ]; then
		last_state="(gone)"
		break
	fi
	last_state="${state}"
	case "${state}" in
	Z*)
		break
		;;
	esac
	sleep "${interval}"
done

echo "pid ${pid} finished (state: ${last_state})"
exit 0
