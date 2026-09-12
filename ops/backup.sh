#!/bin/sh
set -eu

backup_dir=${BACKUP_DIR:-/backups}
retention_days=${BACKUP_RETENTION_DAYS:-30}
interval_seconds=${BACKUP_INTERVAL_SECONDS:-86400}

case "$retention_days:$interval_seconds" in
  *[!0-9:]* | :* | *:) echo "Retenção e intervalo devem ser números positivos" >&2; exit 2 ;;
esac
if [ "$retention_days" -lt 1 ] || [ "$interval_seconds" -lt 1 ]; then
  echo "Retenção e intervalo devem ser números positivos" >&2
  exit 2
fi

umask 077
mkdir -p "$backup_dir"

while true; do
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  target="$backup_dir/planna-$stamp.dump"
  temporary=$(mktemp "$backup_dir/.planna-$stamp.XXXXXX")
  trap 'rm -f "$temporary"' EXIT INT TERM
  pg_dump --format=custom --file="$temporary"
  mv "$temporary" "$target"
  trap - EXIT INT TERM
  find "$backup_dir" -type f -name 'planna-*.dump' -mtime "+$retention_days" -delete
  echo "Backup concluído: $target"
  sleep "$interval_seconds"
done
