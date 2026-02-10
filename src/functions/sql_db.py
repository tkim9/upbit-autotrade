import sqlite3
from datetime import datetime
from typing import Optional
import os

# Get the database directory (two levels up from src/functions/)
FUNCTIONS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(FUNCTIONS_DIR)
PROJECT_ROOT = os.path.dirname(SRC_DIR)
DB_DIR = os.path.join(PROJECT_ROOT, "database")
DB_PATH = os.path.join(DB_DIR, "trade_log.db")

def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Initialize the SQLite database and create the table if it doesn't exist.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Connection to the database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trading_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            decision TEXT NOT NULL,
            confidence_score REAL,
            reason TEXT,
            coin_name TEXT NOT NULL,
            coin_balance REAL,
            krw_balance REAL,
            coin_avg_buy_price REAL,
            coin_krw_price REAL,
            trade_amount REAL,
            is_real_trade INTEGER,
            reflection_timestamp TEXT DEFAULT '',
            result_type TEXT DEFAULT '',
            result_description TEXT DEFAULT '',
            reflection TEXT DEFAULT '',
            profit_loss REAL
        )
    """)

    # Add reflection columns to existing tables (migration)
    # Check if columns exist and add them if they don't
    cursor.execute("PRAGMA table_info(trading_decisions)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'reflection_timestamp' not in columns:
        cursor.execute("ALTER TABLE trading_decisions ADD COLUMN reflection_timestamp TEXT DEFAULT ''")
    if 'result_type' not in columns:
        cursor.execute("ALTER TABLE trading_decisions ADD COLUMN result_type TEXT DEFAULT ''")
    if 'result_description' not in columns:
        cursor.execute("ALTER TABLE trading_decisions ADD COLUMN result_description TEXT DEFAULT ''")
    if 'reflection' not in columns:
        cursor.execute("ALTER TABLE trading_decisions ADD COLUMN reflection TEXT DEFAULT ''")
    if 'profit_loss' not in columns:
        cursor.execute("ALTER TABLE trading_decisions ADD COLUMN profit_loss REAL")

    conn.commit()
    return conn

def insert_decision(
    decision: str,
    coin_name: str,
    confidence_score: Optional[float] = None,
    reason: Optional[str] = None,
    coin_balance: Optional[float] = None,
    krw_balance: Optional[float] = None,
    coin_avg_buy_price: Optional[float] = None,
    coin_krw_price: Optional[float] = None,
    trade_amount: Optional[float] = None,
    is_real_trade: Optional[bool] = None,
    timestamp: Optional[str] = None,
    db_path: str = DB_PATH
) -> int:
    """
    Insert a trading decision record into the database.

    Args:
        decision: Trading decision (buy, sell, hold)
        coin_name: Name of the cryptocurrency
        confidence_score: Confidence score for the trading decision
        reason: Reason for the decision
        coin_balance: Current coin balance (after trade)
        krw_balance: Current KRW balance (after trade)
        coin_avg_buy_price: Average buy price of the coin
        coin_krw_price: Current KRW price of the coin
        trade_amount: Amount traded (KRW for buy, coin amount for sell)
        is_real_trade: Whether this was an actual trade (True) or simulation (False)
        timestamp: Timestamp (ISO format). If None, uses current time
        db_path: Path to the SQLite database file

    Returns:
        ID of the inserted record
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    conn = init_db(db_path)
    cursor = conn.cursor()

    # Convert boolean to integer for SQLite (True -> 1, False -> 0)
    is_real_trade_int = 1 if is_real_trade else 0 if is_real_trade is False else None

    cursor.execute("""
        INSERT INTO trading_decisions
        (timestamp, decision, confidence_score, reason, coin_name, coin_balance,
         krw_balance, coin_avg_buy_price, coin_krw_price, trade_amount, is_real_trade)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        decision,
        confidence_score,
        reason,
        coin_name,
        coin_balance,
        krw_balance,
        coin_avg_buy_price,
        coin_krw_price,
        trade_amount,
        is_real_trade_int
    ))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return record_id

def get_recent_decisions(
    limit: int = 10,
    coin_name: Optional[str] = None,
    db_path: str = DB_PATH
) -> list:
    """
    Retrieve recent trading decisions from the database.

    Args:
        limit: Maximum number of records to retrieve
        coin_name: Optional filter by coin name
        db_path: Path to the SQLite database file

    Returns:
        List of dictionaries containing decision records
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if coin_name:
        cursor.execute("""
            SELECT * FROM trading_decisions
            WHERE coin_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (coin_name, limit))
    else:
        cursor.execute("""
            SELECT * FROM trading_decisions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def get_all_decisions(
    coin_name: Optional[str] = None,
    db_path: str = DB_PATH
) -> list:
    """
    Retrieve all trading decisions from the database.

    Args:
        coin_name: Optional filter by coin name
        db_path: Path to the SQLite database file

    Returns:
        List of dictionaries containing decision records
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if coin_name:
        cursor.execute("""
            SELECT * FROM trading_decisions
            WHERE coin_name = ?
            ORDER BY timestamp DESC
        """, (coin_name,))
    else:
        cursor.execute("""
            SELECT * FROM trading_decisions
            ORDER BY timestamp DESC
        """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def get_decisions_without_reflection(
    coin_name: Optional[str] = None,
    min_hours_old: Optional[int] = 24,
    db_path: str = DB_PATH
) -> list:
    """
    Retrieve trading decisions that don't have reflection data yet.

    Args:
        coin_name: Optional filter by coin name
        min_hours_old: Minimum age in hours (default 24) for trade to be eligible for reflection
        db_path: Path to the SQLite database file

    Returns:
        List of dictionaries containing decision records without reflection
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Calculate the cutoff timestamp
    if min_hours_old:
        from datetime import datetime, timedelta
        cutoff_time = (datetime.now() - timedelta(hours=min_hours_old)).isoformat()

        if coin_name:
            cursor.execute("""
                SELECT * FROM trading_decisions
                WHERE coin_name = ?
                AND (reflection = '' OR reflection IS NULL)
                AND timestamp < ?
                ORDER BY timestamp ASC
            """, (coin_name, cutoff_time))
        else:
            cursor.execute("""
                SELECT * FROM trading_decisions
                WHERE (reflection = '' OR reflection IS NULL)
                AND timestamp < ?
                ORDER BY timestamp ASC
            """, (cutoff_time,))
    else:
        if coin_name:
            cursor.execute("""
                SELECT * FROM trading_decisions
                WHERE coin_name = ?
                AND (reflection = '' OR reflection IS NULL)
                ORDER BY timestamp ASC
            """, (coin_name,))
        else:
            cursor.execute("""
                SELECT * FROM trading_decisions
                WHERE (reflection = '' OR reflection IS NULL)
                ORDER BY timestamp ASC
            """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def update_reflection(
    record_id: int,
    reflection_timestamp: str,
    result_type: str,
    result_description: str,
    reflection: str,
    profit_loss: float,
    db_path: str = DB_PATH
) -> None:
    """
    Update reflection fields for a trading decision record.

    Args:
        record_id: ID of the record to update
        reflection_timestamp: Timestamp when reflection was generated
        result_type: Type of result ('gain', 'loss', 'neutral')
        result_description: Description of the outcome
        reflection: AI-generated reflection text
        profit_loss: Percentage profit/loss as decimal (e.g., 0.10 for 10%)
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trading_decisions
        SET reflection_timestamp = ?,
            result_type = ?,
            result_description = ?,
            reflection = ?,
            profit_loss = ?
        WHERE id = ?
    """, (reflection_timestamp, result_type, result_description, reflection, profit_loss, record_id))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Example usage
    print("Initializing database...")
    conn = init_db()
    print("Database initialized successfully!")

    # Example insert
    record_id = insert_decision(
        decision="buy",
        coin_name="ADA",
        confidence_score=50.0,
        reason="Strong bullish signal on chart",
        coin_balance=1000.0,
        krw_balance=500000.0,
        coin_avg_buy_price=500.0,
        coin_krw_price=520.0,
        trade_amount=100000.0,
        is_real_trade=False
    )
    print(f"Inserted record with ID: {record_id}")

    # Example query
    recent = get_recent_decisions(limit=5)
    print("\nRecent decisions:")
    for decision in recent:
        print(decision)

    conn.close()
