"""Repair an inconsistent migration history before ``migrate`` runs.

Background
----------
PRs #23 and #24 each added a ``core`` migration on parallel branches:
``0005_promptsend`` (the ``PromptSend`` model) and the data migration
``0007_seed_thirty_days_of_prompts``. PR #25 resolved the resulting
migration-graph conflict with the no-op merge migration
``0007_merge_20260517_2159`` and re-pointed the seed migration onto it.

A database that applied the seed migration *before* PR #25 reshaped the
graph -- production did -- ends up with ``0007_seed`` recorded as applied
while its dependency ``0005_promptsend`` never ran. ``manage.py migrate``
runs ``check_consistent_history`` first and aborts with
``InconsistentMigrationHistory``, which crash-loops the container.

(An earlier version of this command tried to patch that by *recording*
the merge migration as applied. That only deepened the hole -- it left
the merge applied while ``0005_promptsend`` was still missing, i.e. the
exact ``0007_merge ... applied before ... 0005_promptsend`` crash.)

Fix
---
Roll the ledger back to ``0006`` by un-recording any 0007 migration that
was applied ahead of ``0005_promptsend``. The ``migrate`` step that
follows in ``start.sh`` then re-applies ``0005_promptsend`` (creating the
missing ``PromptSend`` table), the merge, and the seed in dependency
order. The seed migration skips dates that already have a prompt, so
re-running it creates no duplicates.

Invoked from ``start.sh`` before ``migrate``; a safe, idempotent no-op
once the history is consistent (and on a fresh database).
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

PROMPTSEND = ("core", "0005_promptsend")
MERGE = ("core", "0007_merge_20260517_2159")
SEED = ("core", "0007_seed_thirty_days_of_prompts")


class Command(BaseCommand):
    help = "Roll back 0007 migrations applied before their 0005_promptsend dependency."

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()

        # Inconsistent: a 0007 migration is recorded as applied while its
        # dependency 0005_promptsend is not. Un-record the 0007 nodes so
        # the migrate step that follows re-applies the whole trio in order.
        ahead = [m for m in (MERGE, SEED) if m in applied]
        if PROMPTSEND not in applied and ahead:
            for app, name in ahead:
                recorder.record_unapplied(app, name)
            names = ", ".join(name for _, name in ahead)
            self.stdout.write(
                f"repair: un-recorded {names} (applied before dependency "
                f"core.0005_promptsend); migrate will re-apply in order"
            )
        else:
            self.stdout.write("repair: migration history consistent, nothing to do")
