"""Serialize dispatch with the controller's final historical shutdown check."""
from contextlib import contextmanager

@contextmanager
def dispatch_guard(control):
    with control.db() as cursor:
        cursor.execute("SELECT GET_LOCK('constellation:historical-dispatch-stop',0) AS acquired")
        acquired=cursor.fetchone()['acquired']==1
        try:yield acquired
        finally:
            if acquired:cursor.execute("SELECT RELEASE_LOCK('constellation:historical-dispatch-stop')")
