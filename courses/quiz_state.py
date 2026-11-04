"""Serialize answer writes and submission on the attempt, including on SQLite."""
from contextlib import contextmanager
from time import monotonic, sleep

from django.db import OperationalError, connection, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404

from .models import QuizAttempt


@contextmanager
def serialized_quiz_attempt(attempt_id, user):
    """Take a write lock before reading the state used by a mutation.

    SQLite ignores SELECT FOR UPDATE. A first-statement no-op UPDATE takes
    its writer lock instead; PostgreSQL holds the affected row lock until
    commit. All answer endpoints and submission use this protocol.

    Shared-cache SQLite can return SQLITE_LOCKED without applying its busy
    timeout. Retry *only lock acquisition*, never the yielded mutation, for
    at most five seconds. PDF generation and email stay outside this block.
    """
    deadline = monotonic() + 5
    while True:
        acquired = False
        try:
            with transaction.atomic():
                attempts = QuizAttempt.objects.filter(pk=attempt_id, user=user)
                attempts.update(status=F("status"))
                acquired = True
                yield get_object_or_404(attempts.select_related("course"))
            return
        except OperationalError as error:
            if (acquired or connection.vendor != "sqlite"
                    or "locked" not in str(error).lower()
                    or monotonic() >= deadline):
                raise
            sleep(0.01)
