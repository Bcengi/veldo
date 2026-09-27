"""VELDO-0169: records of a store written before the handout invariant, planted around execute.

Since VELDO-0169 the store refuses, in its commit path, every claim record that hands out work of a
unit whose project the eligibility Gate refuses (control_store.handout_problem), so this branch's
code cannot write the claims an earlier store holds on units that name no project. Suite 84's
upgrade row plants them as main's claim organ decided them, the way 59_veldo_0037_aliases plants a
revision no command could have accepted: around execute, in its own write transaction, with the
entity digest and the next version the store itself computes, so every reader decodes each one
exactly as a committed row. They are never journaled.
"""
import json


def plant(store, conn, eid, kind, data):
    """Write entity `eid` of `kind` with `data` around execute, at its next version."""
    conn.execute('BEGIN IMMEDIATE')
    try:
        row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
        version = (row[0] if row else 0) + 1
        digest = store.digest_of({'kind': kind, 'data': data, 'version': version})
        conn.execute('INSERT INTO entities (id, kind, version, digest, data) VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                     'kind=excluded.kind, version=excluded.version, digest=excluded.digest, data=excluded.data',
                     (eid, kind, version, digest, json.dumps(data, sort_keys=True)))
        conn.execute('COMMIT')
    except BaseException:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise
    return version
