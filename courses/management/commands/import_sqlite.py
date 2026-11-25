"""Import a migrated SQLite copy into a freshly migrated PostgreSQL database."""
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from django.apps import apps
from django.core.management import BaseCommand, CommandError, call_command
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections, transaction
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Import a current SQLite copy into an empty, migrated PostgreSQL database."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path)

    def handle(self, source, **options):
        target = connections[DEFAULT_DB_ALIAS]
        if target.vendor != "postgresql":
            raise CommandError("The default database must be PostgreSQL.")
        source = source.resolve()
        if not source.is_file():
            raise CommandError("The SQLite source file does not exist.")

        with TemporaryDirectory(prefix="elektroakademie-import-") as directory:
            snapshot = Path(directory) / "source.sqlite3"
            try:
                with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
                    with closing(sqlite3.connect(snapshot)) as copy:
                        original.backup(copy)
                self.import_snapshot(snapshot, target)
            except (DatabaseError, sqlite3.Error) as exc:
                # Driver errors can contain values from the fixture.
                raise CommandError(f"Database import aborted ({type(exc).__name__}).") from None

    def import_snapshot(self, snapshot, target):
        alias = "sqlite_import_source"
        connections.databases[alias] = {
            **target.settings_dict,
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": snapshot,
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "OPTIONS": {},
        }
        source = connections[alias]
        try:
            for connection in (source, target):
                executor = MigrationExecutor(connection)
                if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                    raise CommandError("Apply all Django migrations on both databases before import.")
            self.copy_records(alias, target, snapshot.with_suffix(".json"))
        finally:
            source.close()
            del connections[alias]
            del connections.databases[alias]

    def copy_records(self, source, target, fixture):
        models = [m for m in apps.get_models() if m._meta.can_migrate(target)]
        tables = sorted({
            m._meta.db_table
            for m in apps.get_models(include_auto_created=True)
            if m._meta.can_migrate(target)
        })
        generated = {"contenttypes.contenttype", "auth.permission"}
        counts = {m: m._base_manager.using(source).count() for m in models}
        call_command("dumpdata", database=source, use_base_manager=True, output=str(fixture), verbosity=0)

        with transaction.atomic():
            with target.cursor() as cursor:
                quoted = ", ".join(target.ops.quote_name(table) for table in tables)
                cursor.execute(f"LOCK TABLE {quoted} IN ACCESS EXCLUSIVE MODE")
            for model in models:
                if model._meta.label_lower not in generated and model._base_manager.exists():
                    raise CommandError("Use a fresh target database. Existing records were preserved.")

            # Replace migrate's generated metadata with the source IDs so
            # permission memberships and admin log relationships stay intact.
            with target.cursor() as cursor:
                cursor.execute("DELETE FROM auth_permission")
                cursor.execute("DELETE FROM django_content_type")
            try:
                call_command("loaddata", str(fixture), verbosity=0)
            except Exception as exc:
                # loaddata can embed record IDs and values in its error messages.
                raise CommandError(f"Fixture import aborted ({type(exc).__name__}).") from None
            for model, count in counts.items():
                if model._base_manager.count() != count:
                    raise CommandError(f"Record count mismatch for {model._meta.label}.")
            self.restore_sequence_positions(source, target, tables)

        for model, count in counts.items():
            self.stdout.write(f"{model._meta.label}: {count}")
        self.stdout.write(self.style.SUCCESS("Import complete. PostgreSQL verified foreign keys and record counts."))

    def restore_sequence_positions(self, source, target, tables):
        # loaddata resets sequences to MAX(pk). Preserve SQLite's high-water
        # marks too, so IDs deleted before the import won't be allocated again.
        with connections[source].cursor() as cursor:
            cursor.execute("SELECT name, seq FROM sqlite_sequence WHERE seq > 0")
            positions = dict(cursor.fetchall())
        with target.cursor() as cursor:
            for model in apps.get_models(include_auto_created=True):
                table = model._meta.db_table
                if model._meta.proxy or table not in tables or table not in positions:
                    continue
                cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", [table, model._meta.pk.column])
                sequence = cursor.fetchone()[0]
                if sequence:
                    cursor.execute("SELECT setval(%s, %s)", [sequence, positions[table]])
