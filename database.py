import sqlite3
import json
import datetime
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_timestamp TEXT NOT NULL,
            filename TEXT,
            total_cost REAL,
            total_resources INTEGER,
            idle_count INTEGER,
            oversized_count INTEGER,
            storage_waste_count INTEGER,
            potential_savings REAL,
            summary_json TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            resource_id TEXT,
            resource_type TEXT,
            issue_type TEXT,
            current_cost REAL,
            estimated_savings REAL,
            recommendation TEXT,
            priority TEXT,
            FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            step_number INTEGER,
            step_name TEXT,
            status TEXT,
            details TEXT,
            timestamp TEXT,
            FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
        )
    """)

    conn.commit()
    conn.close()


def save_analysis_run(filename, total_cost, total_resources, idle_count,
                      oversized_count, storage_waste_count, potential_savings, summary_dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO analysis_runs
        (run_timestamp, filename, total_cost, total_resources, idle_count,
         oversized_count, storage_waste_count, potential_savings, summary_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.datetime.now().isoformat(),
        filename,
        total_cost,
        total_resources,
        idle_count,
        oversized_count,
        storage_waste_count,
        potential_savings,
        json.dumps(summary_dict)
    ))
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


def save_recommendations(run_id, recommendations_list):
    conn = get_connection()
    cur = conn.cursor()
    for rec in recommendations_list:
        cur.execute("""
            INSERT INTO recommendations
            (run_id, resource_id, resource_type, issue_type, current_cost,
             estimated_savings, recommendation, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            rec.get("resource_id", ""),
            rec.get("resource_type", ""),
            rec.get("issue_type", ""),
            rec.get("current_cost", 0.0),
            rec.get("estimated_savings", 0.0),
            rec.get("recommendation", ""),
            rec.get("priority", "Medium")
        ))
    conn.commit()
    conn.close()


def save_agent_log(run_id, step_number, step_name, status, details):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO agent_logs (run_id, step_number, step_name, status, details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        step_number,
        step_name,
        status,
        details,
        datetime.datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def get_all_runs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM analysis_runs ORDER BY run_timestamp DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recommendations_for_run(run_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recommendations WHERE run_id = ?", (run_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_agent_logs_for_run(run_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM agent_logs WHERE run_id = ? ORDER BY step_number", (run_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

init_db()
