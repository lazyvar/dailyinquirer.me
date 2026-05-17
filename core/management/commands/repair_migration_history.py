"""One-time repair for an inconsistent production migration history.

Background
----------
PR #24 added ``core.0007_seed_thirty_days_of_prompts`` depending on
``core.0006_entry_...``; it deployed and was recorded as applied on
production. PR #25 then resolved a migration-graph conflict by creating
the no-op merge migration ``core.0007_merge_20260517_2159`` and
re-pointing the (already-applied) seed migration's dependency onto it.

The result: production's ``django_migrations`` table has the seed
migration recorded as applied while its new dependency, the merge
migration, is missing. ``manage.py migrate`` runs
``check_consistent_history`` before doing anything and aborts with
``InconsistentMigrationHistory`` -- which crashes the container on boot.

``migrate --fake`` cannot fix this: it runs the same consistency check
first. The fix has to write the missing ledger row directly, which is
what this command does. It is invoked from ``start.sh`` before
``migrate`` and is safe to keep -- it is a precise, idempotent no-op
once the history is consistent (and on any fresh database).
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

SEED = ("core", "0007_seed_thirty_days_of_prompts")
MERGE = ("core", "0007_merge_20260517_2159")


class Command(BaseCommand):
    help = "Record the 0007 merge migration if its dependent was applied without it."

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()

        if SEED in applied and MERGE not in applied:
            recorder.record_applied(*MERGE)
            self.stdout.write(
                f"repair: recorded {MERGE[0]}.{MERGE[1]} as applied "
                f"(dependent {SEED[1]} was applied without it)"
            )
        else:
            self.stdout.write("repair: migration history consistent, nothing to do")
