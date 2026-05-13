import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("FEEDBACK_DB_PATH", "feedback_log.db")

def get_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise e

def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT,
                timestamp DATETIME,
                user_input TEXT,
                agent_response TEXT,
                feedback_score INTEGER,
                optional_comment TEXT
            )
        ''')
        conn.commit()
        logger.info("Feedback database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

def log_feedback(thread_id: str, user_input: str, agent_response: str, feedback_score: int, optional_comment: str = ""):
    """Log user feedback to the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat() + "Z"
        cursor.execute('''
            INSERT INTO feedback (thread_id, timestamp, user_input, agent_response, feedback_score, optional_comment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (thread_id, timestamp, user_input, agent_response, feedback_score, optional_comment))
        conn.commit()
        logger.info(f"Feedback logged successfully for thread: {thread_id}")
    except sqlite3.Error as e:
        logger.error(f"Error logging feedback: {e}")
    finally:
        if conn:
            conn.close()

def get_negative_feedback():
    """Retrieve all feedback records with a negative score (-1)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM feedback WHERE feedback_score = -1')
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries for easier processing
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        return results
    except sqlite3.Error as e:
        logger.error(f"Error retrieving negative feedback: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Initialize the database when the module is imported
init_db()
