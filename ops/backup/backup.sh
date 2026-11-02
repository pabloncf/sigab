#!/usr/bin/env bash
# Credentials use libpq environment/PGPASSFILE; only the public age key is needed.
set -euo pipefail
umask 077
: "${PGDATABASE:?Set PGDATABASE}"
: "${BACKUP_DIR:?Set BACKUP_DIR}"
: "${AGE_RECIPIENT:?Set AGE_RECIPIENT}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
work=$(mktemp -d "$BACKUP_DIR/.backup.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# pipefail prevents publishing an encrypted but incomplete dump.
pg_dump --format=custom --no-owner --no-acl --no-password |
  age --recipient "$AGE_RECIPIENT" > "$work/database.dump.age"
# Metadata is inside the protected directory, and contains no connection details.
python3 - "$work" "$started" <<'PY'
import hashlib, json, pathlib, sys
from datetime import datetime, timezone
root = pathlib.Path(sys.argv[1])
with (root / "database.dump.age").open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
(root / "manifest.json").write_text(json.dumps({
    "schema": "sigab.backup.v1", "snapshot_started_at": sys.argv[2],
    "completed_at": datetime.now(timezone.utc).isoformat(), "sha256": digest,
}) + "\n")
PY
# Unique directory; no overwrite of an existing backup.
destination="$BACKUP_DIR/$(date -u +%Y%m%dT%H%M%SZ)-${work##*.}"
mv "$work" "$destination"
trap - EXIT
printf '%s\n' "$destination"
