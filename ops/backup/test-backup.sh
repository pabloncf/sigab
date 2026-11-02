#!/usr/bin/env bash
# Synthetic integration exercise. Run only with the dedicated CI/test cluster.
set -euo pipefail
umask 077
cd "$(dirname "$0")/../../backend"
work=$(mktemp -d)
export PGDATABASE="sigab_fixture_$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
createdb --no-password "$PGDATABASE"
cleanup() { dropdb --no-password "$PGDATABASE"; rm -rf "$work"; }
trap cleanup EXIT
export DATABASE_URL="postgresql://:${PGPORT:-5432}/${PGDATABASE}"
uv run --frozen --no-dev python manage.py migrate --noinput
uv run --frozen --no-dev python manage.py shell --verbosity 0 <<'PY'
import uuid
from sigab.models import Account, Organization, Unit, StorageLocation, EquipmentType, Item, Person, Membership, Role, Grant
from sigab.services import CommandContext, record_incorporation, checkout_item, return_item
org = Organization.objects.create(name="Backup synthetic organization")
unit = Unit.objects.create(organization=org, name="Synthetic unit", code="TEST")
location = StorageLocation.objects.create(organization=org, unit=unit, name="Synthetic storage", code="R")
type_ = EquipmentType.objects.create(organization=org, name="Synthetic type", classification="individual")
account = Account.objects.create_user(username="backup-test", organization=org)
role = Role.objects.create(organization=org, name="Test operator", permissions=["movement.checkout", "movement.return", "item.view"])
Grant.objects.create(organization=org, account=account, role=role, scope_type="organization")
person = Person.objects.create(organization=org, name="Synthetic person")
Membership.objects.create(organization=org, person=person, main_unit=unit, registration="TEST")
item = Item.objects.create(organization=org, unit=unit, storage_location=location, equipment_type=type_, serial_number="SYN-BACKUP")
ctx = CommandContext(account, org, "backup-exercise")
record_incorporation(ctx, item)
checkout_item(ctx, item_id=item.id, recipient_id=person.id, confirmed=True, idempotency_key=uuid.uuid4())
return_item(ctx, item_id=item.id, condition="fit", confirmed=True, idempotency_key=uuid.uuid4())
PY
export AGE_IDENTITY="$work/key.agekey"
age-keygen -o "$AGE_IDENTITY" 2>/dev/null
export AGE_RECIPIENT
AGE_RECIPIENT=$(age-keygen -y "$AGE_IDENTITY")
export BACKUP_DIR="$work/backups"
export BACKUP_PATH
BACKUP_PATH=$(../ops/backup/backup.sh)
export RESTORE_TEST_ISOLATED=yes
export REPORT_PATH="$work/restore.json"
../ops/backup/restore-test.sh
python3 - "$REPORT_PATH" "$BACKUP_PATH" <<'PY'
import json, pathlib, stat, sys
report = json.loads(pathlib.Path(sys.argv[1]).read_text())
assert report['restored_counts'] == {'Organization': 1, 'Item': 1, 'Movement': 3, 'AuditEvent': 3}, report
root = pathlib.Path(sys.argv[2])
assert stat.S_IMODE(root.stat().st_mode) == 0o700
assert stat.S_IMODE((root / 'database.dump.age').stat().st_mode) == 0o600
print(json.dumps(report, indent=2))
PY
# Invalid key and altered ciphertext must fail without a success report.
age-keygen -o "$work/wrong.agekey" 2>/dev/null
if AGE_IDENTITY="$work/wrong.agekey" REPORT_PATH="$work/wrong.json" ../ops/backup/restore-test.sh; then
  echo 'Wrong key unexpectedly accepted' >&2; exit 1
fi
[[ ! -e "$work/wrong.json" ]]
printf 'corruption' >> "$BACKUP_PATH/database.dump.age"
if REPORT_PATH="$work/corrupt.json" ../ops/backup/restore-test.sh; then
  echo 'Corrupt backup unexpectedly accepted' >&2; exit 1
fi
[[ ! -e "$work/corrupt.json" ]]
# Even if someone updates the untrusted checksum, age must reject tampering.
python3 - "$BACKUP_PATH" <<'PYHASH'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
manifest = json.loads((root / 'manifest.json').read_text())
with (root / 'database.dump.age').open('rb') as stream:
    manifest['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
(root / 'manifest.json').write_text(json.dumps(manifest))
PYHASH
if REPORT_PATH="$work/tampered.json" ../ops/backup/restore-test.sh; then
  echo 'Unauthenticated ciphertext unexpectedly accepted' >&2; exit 1
fi
[[ ! -e "$work/tampered.json" ]]
# A failed dump must not publish even a partial backup.
if PGDATABASE=nonexistent_synthetic_database ../ops/backup/backup.sh; then
  echo 'Failed dump unexpectedly accepted' >&2; exit 1
fi
[[ $(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l) -eq 1 ]]
[[ $(psql --no-password -Atc "SELECT count(*) FROM pg_database WHERE datname LIKE 'sigab_restore_%'") -eq 0 ]]
if [[ -n "${EXERCISE_REPORT_PATH:-}" ]]; then
  cp "$REPORT_PATH" "$EXERCISE_REPORT_PATH"
  # Synthetic CI evidence contains no secrets and must be readable by artifact upload.
  chmod 644 "$EXERCISE_REPORT_PATH"
fi
echo 'Encrypted backup, restoration, failure cases and cleanup passed.'
