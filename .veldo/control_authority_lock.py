"""The store authority lock check shared by API and owner configuration writers.

Keep this check independent of the API judge's command and read-model imports:
setup and service startup use it even when they do not construct an API judge.
"""
import fcntl
import os

LOCK_NAME = 'authority.lock'


def authority_problem(lock, conn):
    """Why this process may not run the authority's commands and reads on `conn`, or None: `lock` must be
    an open descriptor of the stable lock file beside the store `conn` opened, on which this process holds
    the exclusive flock (taking it again on the same descriptor succeeds only for its holder). A store the
    connection cannot name is a store error (sqlite3.Error), as any unreadable store is."""
    rows = conn.execute('PRAGMA database_list').fetchall()
    store = next((row[2] for row in rows if row[1] == 'main' and row[2]), None)
    if store is None or type(lock) is not int:
        return 'missing_authority:not_the_authority'
    try:
        held, named = os.fstat(lock), os.stat(os.path.join(os.path.dirname(store), LOCK_NAME))
        if (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino):
            return 'missing_authority:not_the_authority'
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 'missing_authority:not_the_authority'
    return None

