import sqlite3
from typing import Any

def get_verdicts_by_card(conn: sqlite3.Connection, run_id: str) -> dict[str, list[dict[str, Any]]]:
    """
    MF-4: Extracts manual-verdict aggregation logic from the router layer.
    Retrieves verdicts for a given run and buckets them by card_id.
    """
    verdicts = conn.execute(
        "SELECT * FROM manual_verdicts WHERE run_id = ?", (run_id,)
    ).fetchall()
    
    verdicts_by_card = {}
    for v in verdicts:
        vd = dict(v)
        verdicts_by_card.setdefault(vd["card_id"], []).append(vd)
        
    return verdicts_by_card
