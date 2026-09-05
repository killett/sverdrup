#!/bin/sh
# Stage-1 per-leg launcher — parks on the gate, relaunches on a clean halt.
#
# Owner pin 156(b): when the in-run watchdog halts a leg, THIS parks again
# until the box recovers and relaunches it. The resume is pin 121's and is
# already bit-identity tested — no second resume path is built here.
#
# Usage:  sh scripts/stage1_leg_launcher.sh <tile> [m] [maxiter]
#
# Exit codes from the leg:
#   0   completed — the evidence row is written; stop.
#   75  STAGE1_HEADROOM_HALT_EXIT — clean headroom halt; park and relaunch.
#   76  STAGE1_GATE_REFUSED_EXIT — the box moved between this check and the
#       leg's own re-read; a WAIT, not a fault. Park and relaunch.
#   *   crash — STOP and report. A crash is not relaunched blind.
set -e
cd /workspace

TILE=${1:?usage: stage1_leg_launcher.sh <tile> [m] [maxiter]}
M=${2:-100}
MAXITER=${3:-1200}
OUT="logs/leg_${TILE}"
mkdir -p "$OUT"

# Pin 155: 2 x the MEASURED nine-window peak (4951.16 MiB) = 9902.33, and
# the leg re-reads it itself at start. GATE parks ABOVE that by GATE_MARGIN
# because the box moves between the two checks: leg 3's first attempt read
# 10,009 MiB here and 9,891.58 one second later, refused correctly, and was
# then read as a crash. 9903 + 256 covers a dip of that order.
GATE_MARGIN=256
GATE=10159
HALT_EXIT=75
GATE_REFUSED_EXIT=76
ATTEMPT=0

log() { printf '%s %s\n' "$(date -Iseconds)" "$1" >> "$OUT/launcher.log"; }

while :; do
  ATTEMPT=$((ATTEMPT + 1))

  # Park until the box clears the launch gate.
  while :; do
    AVAIL=$(( $(awk '/MemAvailable/{print $2}' /proc/meminfo) / 1024 ))
    [ "$AVAIL" -ge "$GATE" ] && break
    log "waiting for headroom: ${AVAIL} MiB < ${GATE} MiB (attempt ${ATTEMPT})"
    sleep 300
  done
  log "gate CLEARED: ${AVAIL} MiB >= ${GATE} MiB — launching ${TILE} (attempt ${ATTEMPT})"

  nohup pixi run python -u scripts/phase14_stage1_run.py run "$TILE" \
    --m "$M" --maxiter "$MAXITER" >> "$OUT/leg.log" 2>&1 &
  WRAP=$!
  echo "$WRAP" > "$OUT/wrapper.pid"

  # Resolve the REAL python pid, disambiguated BY TILE. A bare pgrep pattern
  # two jobs can match has produced false completion reports three times and
  # made one sampler follow the wrong process.
  i=0
  PID=""
  while [ $i -lt 120 ]; do
    PID=$(pgrep -f "phase14_stage1_run.py run ${TILE}" | while read -r p; do
            case "$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)" in
              */.pixi/envs/default/bin/python*run\ "$TILE"*) echo "$p"; break;;
            esac
          done)
    [ -n "$PID" ] && break
    i=$((i + 1))
    sleep 1
  done
  echo "$PID" > "$OUT/leg.pid"
  log "real pid ${PID} (wrapper ${WRAP})"

  # Sample at the SAME cadence the in-run tracker uses (pin 156c), so the two
  # cannot disagree about the same run the way they did on leg 2.
  START=$(date +%s)
  while kill -0 "$PID" 2>/dev/null; do
    HWM=$(awk '/VmHWM/{print $2}' /proc/$PID/status 2>/dev/null || echo 0)
    RSS=$(awk '/VmRSS/{print $2}' /proc/$PID/status 2>/dev/null || echo 0)
    SWP=$(awk '/VmSwap/{print $2}' /proc/$PID/status 2>/dev/null || echo 0)
    AVAIL=$(( $(awk '/MemAvailable/{print $2}' /proc/meminfo) / 1024 ))
    printf '%s peak_rss=%sMiB rss=%sMiB vm_swap=%sMiB mem_avail=%sMiB elapsed_h=%s\n' \
      "$(date -Iseconds)" "$((HWM / 1024))" "$((RSS / 1024))" "$((SWP / 1024))" \
      "$AVAIL" "$(( ($(date +%s) - START) / 3600 ))" >> "$OUT/vmhwm.log"
    sleep 60
  done

  wait "$WRAP" 2>/dev/null && RC=0 || RC=$?
  log "leg exited rc=${RC} after $(( $(date +%s) - START ))s"

  if [ "$RC" -eq 0 ]; then
    log "COMPLETED — evidence row written. Launcher stops."
    exit 0
  fi
  if [ "$RC" -eq "$HALT_EXIT" ]; then
    # Pin 156(b). Not a crash: the windows are on disk and the relaunch
    # resumes from them.
    log "CLEAN HEADROOM HALT (rc=${HALT_EXIT}) — parking, then relaunching to resume"
    sleep 600
    continue
  fi
  if [ "$RC" -eq "$GATE_REFUSED_EXIT" ]; then
    # The leg's own gate re-read refused: the box moved under us. A WAIT,
    # not a fault — park and try again at the top of the next cycle.
    log "GATE REFUSED at the leg's own re-read (rc=${GATE_REFUSED_EXIT}) — the box moved; parking"
    sleep 300
    continue
  fi
  log "⛔ CRASH rc=${RC} — NOT relaunched. Stop and report (a crash is not a halt)."
  exit "$RC"
done
