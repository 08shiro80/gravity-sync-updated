#!/bin/bash
# Gravity Sync File Watcher
# Watches Pi-hole config files for changes and triggers a push to the secondary instance.
# Requires: inotify-tools (apt install inotify-tools)

WATCH_FILES="/etc/pihole/gravity.db /etc/pihole/hosts/custom.list /etc/pihole/pihole.toml"
COOLDOWN=30
LOGFILE="/var/log/gravity-sync-watch.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "${LOGFILE}"
}

log "Gravity Sync watcher started"

while true; do
    CHANGED=$(inotifywait -e modify -e create --format '%w' ${WATCH_FILES} 2>/dev/null)
    log "Change detected: ${CHANGED}"
    sleep ${COOLDOWN}
    if /usr/local/bin/gravity-sync push >> "${LOGFILE}" 2>&1; then
        log "Push completed successfully"
    else
        log "Push failed"
    fi
done
