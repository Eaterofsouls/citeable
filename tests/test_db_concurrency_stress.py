import sqlite3
import threading
import time
import pytest
from pathlib import Path
from areos.db.connection import get_connection, get_db_path
from areos.db.context import write_as


def test_concurrent_txn_context_isolation_multithreaded():
    """Verify concurrent worker threads maintain independent _txn_context rows without crosstalk."""
    db_path = get_db_path()
    errors = []

    def worker(worker_id: int):
        try:
            conn = get_connection(db_path)
            for i in range(10):
                actor_name = f"worker_{worker_id}_{i}"
                reason_text = f"reason_{worker_id}_{i}"
                with write_as(conn, actor=actor_name, reason=reason_text):
                    row = conn.execute("SELECT actor, reason FROM _txn_context WHERE id = 1").fetchone()
                    if row["actor"] != actor_name or row["reason"] != reason_text:
                        errors.append(f"Crosstalk detected in thread {worker_id}: expected ({actor_name}, {reason_text}), got {row}")
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"Exception in worker {worker_id}: {e}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrency errors encountered: {errors}"


def test_concurrent_reads_during_writes_wal_mode():
    """Verify concurrent reads do not block or crash while a write transaction is executing."""
    db_path = get_db_path()
    errors = []
    stop_event = threading.Event()

    def reader_loop():
        try:
            conn = get_connection(db_path)
            while not stop_event.is_set():
                row = conn.execute("SELECT count(*) as c FROM knowledge").fetchone()
                assert row["c"] > 0
                time.sleep(0.002)
        except Exception as e:
            errors.append(f"Reader error: {e}")

    readers = [threading.Thread(target=reader_loop) for _ in range(4)]
    for r in readers:
        r.start()

    # Perform writes in main thread
    conn = get_connection(db_path)
    for i in range(5):
        with write_as(conn, actor="stress_tester", reason="concurrency check"):
            conn.execute("UPDATE kb_metrics SET value = ? WHERE key = 'version'", (str(i + 1),))
        time.sleep(0.01)

    stop_event.set()
    for r in readers:
        r.join()

    assert len(errors) == 0, f"Reader errors during writes: {errors}"
