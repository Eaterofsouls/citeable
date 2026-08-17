# areos/services/auto_apply.py
#
# Core logic for Task 2e: Auto-apply gate and counters.
#
# CONTRACT:
#   - Auto-apply ships hardcoded to always return False for v1.
#   - approval/rejection counters per source are incremented upon decision.

from __future__ import annotations
import logging
import sqlite3
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def is_auto_apply_eligible(source_url: str, db_path: str) -> bool:
    """
    Determine if a claim sourced from this URL should be auto-applied
    without human review.
    
    For v1 (per Playbook 7.3 and Task 2e), this is HARDCODED to False.
    The true 25-in-a-row graduation trigger is deferred.
    """
    return False

def record_approval(conn: sqlite3.Connection, source_url: str) -> None:
    """
    Increment the approved_count for the source matching this URL.
    """
    if not source_url:
        return
        
    domain = urlparse(source_url).netloc
    if not domain:
        domain = source_url
        
    conn.execute("""
        UPDATE sources 
        SET approved_count = approved_count + 1 
        WHERE url = ? OR domain = ?
    """, (source_url, domain))

def record_rejection(conn: sqlite3.Connection, source_url: str) -> None:
    """
    Increment the rejected_count for the source matching this URL.
    """
    if not source_url:
        return
        
    domain = urlparse(source_url).netloc
    if not domain:
        domain = source_url
        
    conn.execute("""
        UPDATE sources 
        SET rejected_count = rejected_count + 1 
        WHERE url = ? OR domain = ?
    """, (source_url, domain))
