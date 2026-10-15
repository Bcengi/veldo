"""VELDO-0182: copy_chroma against chromadb's own Rust local HNSW writer, with the index itself as evidence.

Run with an interpreter that has chromadb (1.5.9 was measured):
    python chroma_rust_copy.py <repository root> <scratch directory> [result.json]

A writer process persists a Chroma collection in bursts (batch_size 10, sync_threshold 20, so the HNSW files
are rewritten every 20 adds) while copy_chroma copies the directory again and again. Each copy is opened in a
duplicate of itself, and every id its SQLite holds is searched for through the HNSW index by the id's own
embedding; the copy holds when every id is its own nearest neighbour. The falsifier copies the segment files,
waits for the writer's next persist, then backs up SQLite without the stamp check: the copy's SQLite then
claims a sequence its index files lack, the log below it is purged, and ids go missing from the index.
"""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import sqlite3
import subprocess
import sys
import time

DIMENSIONS, NAME = 16, 'veldo-copy'
CONFIGURATION = {'hnsw': {'batch_size': 10, 'sync_threshold': 20}}


def vector(identity):
    rng = random.Random(identity)
    return [rng.gauss(0, 1) for _ in range(DIMENSIONS)]


def write(source, stop):
    import chromadb
    client = chromadb.PersistentClient(path=source)
    collection = client.get_or_create_collection(NAME, configuration=CONFIGURATION)
    n, rng = 0, random.Random(182)
    while not os.path.exists(stop):
        for _ in range(rng.randint(5, 45)):
            collection.add(ids=['id-%d' % n], embeddings=[vector('id-%d' % n)])
            n += 1
        time.sleep(rng.uniform(0.1, 1.2))
    print(n)


def verify(copy, scratch):
    """Every id the copy's SQLite holds is found through its HNSW index by its own embedding."""
    import chromadb
    view = Path(scratch) / ('view-' + Path(copy).name)
    shutil.copytree(copy, view, symlinks=True)
    try:
        client = chromadb.PersistentClient(path=str(view))
        collection = client.get_collection(NAME)
        ids = collection.get(include=[])['ids']
        found = 0
        for start in range(0, len(ids), 100):
            batch = ids[start:start + 100]
            answer = collection.query(query_embeddings=[vector(i) for i in batch], n_results=1, include=[])
            found += sum(1 for i, near in zip(batch, answer['ids']) if near and near[0] == i)
        return len(ids), found
    finally:
        shutil.rmtree(view)


def stamps(C, source):
    return C.segment_stamps(source)


def main():
    root, scratch = Path(sys.argv[1]), Path(sys.argv[2])
    scratch.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('chroma_rust_check', root / '.veldo/control_memory_check.py')
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)
    C.QUIET = 0.3
    source, stop = scratch / 'source', scratch / 'stop'
    writer = subprocess.Popen([sys.executable, __file__, '--write', str(source), str(stop)], stdout=subprocess.PIPE, text=True)
    copies, busy, falsifier = [], 0, []
    try:
        while not (source / 'chroma.sqlite3').exists() or not stamps(C, source):
            time.sleep(0.2)
        spread = random.Random(1820)
        for i in range(25):
            # Spread over the writer's bursts and pauses, so copies start mid-burst as well as in a pause.
            time.sleep(spread.uniform(0, 1.5))
            target = scratch / ('copy-%d' % i)
            try:
                attempts = C.copy_chroma(source, target, 'memory_kb', attempts=12)
            except C.M.Refused:
                busy += 1
                continue
            total, found = verify(target, scratch)
            copies.append(dict(attempts=attempts, ids=total, found_through_index=found))
            shutil.rmtree(target)
        for i in range(3):
            # The falsifier: segment files first, then the writer's next persist, then SQLite, unchecked.
            target = scratch / ('unchecked-%d' % i)
            before = stamps(C, source)
            target.mkdir()
            for name in before:
                (target / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / name, target / name)
            deadline = time.monotonic() + 30
            while stamps(C, source) == before and time.monotonic() < deadline:
                time.sleep(0.01)
            time.sleep(0.2)
            C.backup(source / 'chroma.sqlite3', target / 'chroma.sqlite3')
            total, found = verify(target, scratch)
            falsifier.append(dict(ids=total, found_through_index=found))
            shutil.rmtree(target)
    finally:
        stop.write_text('stop')
        written = int(writer.communicate(timeout=60)[0].strip() or 0)
    with contextlib.closing(sqlite3.connect(source / 'chroma.sqlite3')) as conn:
        persisted = conn.execute('SELECT MAX(seq_id) FROM max_seq_id').fetchone()[0]
    import chromadb
    result = dict(chromadb=chromadb.__version__, configuration=CONFIGURATION, written=written, persisted_seq=persisted,
                  copies=copies, copies_busy=busy, falsifier=falsifier,
                  copies_hold=bool(copies) and all(c['ids'] > 0 and c['found_through_index'] == c['ids'] for c in copies),
                  falsifier_loses=any(f['found_through_index'] < f['ids'] for f in falsifier))
    shutil.rmtree(scratch)
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(text)
    print(text)
    return 0 if result['copies_hold'] and result['falsifier_loses'] else 1


if __name__ == '__main__':
    if sys.argv[1] == '--write':
        write(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
