"""Repair an inconsistent production migration history before ``migrate``.

Background
----------
PR #24 added ``core.0007_seed_thirty_days_of_prompts``; PR #23/#25 then
introduced ``core.0005_promptsend`` and the no-op merge migration
``core.0007_merge_20260517_2159``, and re-pointed the seed migration's
dependency onto the merge.

On production the 0007 tip -- the merge and/or seed migrations -- ended
up recorded as applied in ``django_migrations`` while the merge's
dependency ``core.0005_promptsend`` never was. ``manage.py migrate``
runs ``check_consistent_history`` before doing anything and aborts with
``InconsistentMigrationHistory`` -- crashing the container on boot.
``migrate --fake`` cannot help: it runs the same check first.

This command removes the orphaned 0007 ledger rows so ``migrate`` can
replay ``0005_promptsend -> 0007_merge -> 0007_seed`` forward, creating
the missing ``core_promptsend`` table. The seed migration only inserts
prompts for dates that have none, so replaying it is safe.

It runs from ``start.sh`` before ``migrate`` and is a precise,
idempotent no-op once history is consistent (and on any fresh database).
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

PROMPTSEND = ("core", "0005_promptsend")
# The 0007 tip that depends (transitively) on 0005_promptsend. Order does
# not matter -- un-recording is a row delete -- but the merge must go too:
# leaving the seed without the merge would just shift the inconsistency.
TIP = [
    ("core", "0007_merge_20260517_2159"),
    ("core", "0007_seed_thirty_days_of_prompts"),
]


class Command(BaseCommand):
    help = "Un-record the 0007 tip if it was applied without 0005_promptsend."

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()

        orphaned = [m for m in TIP if m in applied]
        if PROMPTSEND not in applied and orphaned:
            for migration in orphaned:
                recorder.record_unapplied(*migration)
                self.stdout.write(
                    f"repair: un-recorded {migration[0]}.{migration[1]} "
                    f"(applied without dependency {PROMPTSEND[1]})"
                )
        else:
            self.stdout.write(
                "repair: migration history consistent, nothing to do")
