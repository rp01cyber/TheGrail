#!/usr/bin/env bash
# Nightly backup of the database and uploaded files.
# Schedule with cron:  0 3 * * * /opt/pentestnotes/deploy/backup.sh
set -euo pipefail

APP_DIR="/opt/pentestnotes"
DEST="${PN_BACKUP_DIR:-/opt/pentestnotes/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST"

# .backup makes a consistent copy even while the app is running (WAL-safe).
sqlite3 "$APP_DIR/data/db.sqlite3" ".backup '$DEST/db-$STAMP.sqlite3'"

# Uploaded files.
tar czf "$DEST/media-$STAMP.tar.gz" -C "$APP_DIR" media

# Keep the last 14 of each; delete older.
ls -1t "$DEST"/db-*.sqlite3    | tail -n +15 | xargs -r rm -f
ls -1t "$DEST"/media-*.tar.gz  | tail -n +15 | xargs -r rm -f

echo "backup complete: $DEST (db-$STAMP.sqlite3, media-$STAMP.tar.gz)"
# For off-box safety, copy $DEST elsewhere too (Linode Object Storage, rsync, etc.).
