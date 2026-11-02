#!/usr/bin/env bash
# Run on an isolated PostgreSQL server, never against a production cluster.
set -euo pipefail
umask 077
: "${PGHOST:?Set isolated PGHOST}"
: "${PGUSER:?Set isolated PGUSER}"
: "${BACKUP_PATH:?Set BACKUP_PATH}"
: "${AGE_IDENTITY:?Set AGE_IDENTITY}"
: "${REPORT_PATH:?Set REPORT_PATH}"
: "${RESTORE_TEST_ISOLATED:?Set RESTORE_TEST_ISOLATED=yes on an isolated server}"
[[ "$RESTORE_TEST_ISOLATED" == yes ]] || exit 2
python3 - "$AGE_IDENTITY" <<'PYKEY'
import pathlib, stat, sys
key = pathlib.Path(sys.argv[1])
if not key.is_file() or stat.S_IMODE(key.stat().st_mode) & 0o077:
    sys.exit("Private age identity must be a file with mode 0600 or stricter")
PYKEY
started=$(python3 -c 'import time; print(time.monotonic())')
# Authenticate ciphertext fully before any database creation. The temporary dump
# must live on encrypted storage (or tmpfs) accessible only to this operator.
work=$(mktemp -d)
database="sigab_restore_$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
created=no
cleanup() {
  status=$?
  if [[ "$created" == yes ]]; then
    if ! dropdb --no-password "$database"; then
      printf 'Cleanup failed for disposable database %s\n' "$database" >&2
      status=1
    fi
  fi
  rm -rf "$work"
  exit "$status"
}
trap cleanup EXIT
python3 - "$BACKUP_PATH" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
manifest = json.loads((root / "manifest.json").read_text())
with (root / "database.dump.age").open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
if manifest.get("schema") != "sigab.backup.v1" or digest != manifest.get("sha256"):
    sys.exit("Backup checksum/schema mismatch")
PY
age --decrypt --identity "$AGE_IDENTITY" "$BACKUP_PATH/database.dump.age" > "$work/database.dump"
createdb --no-password --template=template0 "$database"
created=yes
pg_restore --no-password --exit-on-error --single-transaction --no-owner --no-acl \
  --dbname="$database" "$work/database.dump"
# Django reads DATABASE_URL; connection credentials never appear as CLI arguments.
export PGDATABASE="$database"
# Leave user/password/host to libpq's PG* environment (including PGPASSFILE).
# Only the disposable database and port are selected in Django's URL.
export DATABASE_URL="postgresql://:${PGPORT:-5432}/$database"
cd "$(dirname "$0")/../../backend"
uv run --frozen --no-dev python manage.py check
uv run --frozen --no-dev python manage.py migrate --check
uv run --frozen --no-dev python manage.py verify_audit_chain
# An empty schema is not a successful application restoration.
counts=$(uv run --frozen --no-dev python manage.py shell --verbosity 0 -c \
  'import json; from sigab.models import Organization, Item, Movement, AuditEvent; assert Organization.objects.exists(), "No organizations restored"; print(json.dumps({m.__name__: m.objects.count() for m in (Organization, Item, Movement, AuditEvent)}))')
python3 - "$REPORT_PATH" "$started" "$counts" "$BACKUP_PATH" <<'PY'
import json, pathlib, sys, time
from datetime import datetime, timezone
elapsed = round(time.monotonic() - float(sys.argv[2]), 3)
report = {
    "schema": "sigab.restore-test.v1", "completed_at": datetime.now(timezone.utc).isoformat(),
    "restore_and_checks_seconds": elapsed, "database_rto_within_4h": elapsed <= 14400,
    "audit_chain": "passed", "migrations": "current", "application_check": "passed",
    "production_rpo": "not_measured", "full_service_rto": "not_measured",
    "restored_counts": json.loads(sys.argv[3]),
    "backup": json.loads((pathlib.Path(sys.argv[4]) / 'manifest.json').read_text()),
}
# Exclusive create prevents replacing evidence from an earlier exercise.
with pathlib.Path(sys.argv[1]).open('x') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
if elapsed > 14400:
    sys.exit('Database restore exceeded 4 hours')
PY
