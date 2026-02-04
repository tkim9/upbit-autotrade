import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = "trade_log.db"

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
            is_real_trade INTEGER
        )
    """)

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
