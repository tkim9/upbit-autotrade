"""
Pytest tests for sql_db module functions.
Tests the new reflection-related database functions.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta

from functions.sql_db import (
    init_db,
    insert_decision,
    get_decisions_without_reflection,
    update_reflection
)


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    # Create a temporary file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Initialize the database
    conn = init_db(db_path)
    conn.close()

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def populated_db(test_db):
    """Create a database with sample trade data."""
    # Insert sample trades with different timestamps

    # Trade 1: 48 hours old, no reflection
    old_timestamp = (datetime.now() - timedelta(hours=48)).isoformat()
    insert_decision(
        decision="buy",
        coin_name="ADA",
        confidence_score=75.0,
        reason="Strong bullish signal",
        coin_balance=1000.0,
        krw_balance=500000.0,
        coin_avg_buy_price=500.0,
        coin_krw_price=520.0,
        trade_amount=100000.0,
        is_real_trade=False,
        timestamp=old_timestamp,
        db_path=test_db
    )

    # Trade 2: 30 hours old, no reflection
    medium_timestamp = (datetime.now() - timedelta(hours=30)).isoformat()
    insert_decision(
        decision="sell",
        coin_name="ADA",
        confidence_score=60.0,
        reason="Overbought conditions",
        coin_balance=500.0,
        krw_balance=800000.0,
        coin_avg_buy_price=500.0,
        coin_krw_price=560.0,
        trade_amount=500.0,
        is_real_trade=False,
        timestamp=medium_timestamp,
        db_path=test_db
    )

    # Trade 3: 12 hours old, no reflection (too recent)
    recent_timestamp = (datetime.now() - timedelta(hours=12)).isoformat()
    insert_decision(
        decision="hold",
        coin_name="ADA",
        confidence_score=0.0,
        reason="Market unclear",
        coin_balance=500.0,
        krw_balance=800000.0,
        coin_avg_buy_price=500.0,
        coin_krw_price=550.0,
        trade_amount=0.0,
        is_real_trade=False,
        timestamp=recent_timestamp,
        db_path=test_db
    )

    # Trade 4: 50 hours old, already has reflection
    old_with_reflection = (datetime.now() - timedelta(hours=50)).isoformat()
    record_id = insert_decision(
        decision="buy",
        coin_name="BTC",
        confidence_score=80.0,
        reason="Breakout confirmed",
        coin_balance=0.5,
        krw_balance=10000000.0,
        coin_avg_buy_price=50000000.0,
        coin_krw_price=50500000.0,
        trade_amount=5000000.0,
        is_real_trade=False,
        timestamp=old_with_reflection,
        db_path=test_db
    )

    # Add reflection to trade 4
    update_reflection(
        record_id=record_id,
        reflection_timestamp=datetime.now().isoformat(),
        result_type="gain",
        result_description="Price increased 5%",
        reflection="Good decision based on technical analysis",
        profit_loss=0.05,
        db_path=test_db
    )

    return test_db


class TestDatabaseSchema:
    """Test that the database schema is correct."""

    def test_init_db_creates_table(self, test_db):
        """Test that init_db creates the trading_decisions table."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='trading_decisions'
        """)
        assert cursor.fetchone() is not None

        conn.close()

    def test_reflection_columns_exist(self, test_db):
        """Test that all reflection columns are present."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(trading_decisions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        # Check all reflection columns exist with correct types
        assert 'reflection_timestamp' in columns
        assert 'result_type' in columns
        assert 'result_description' in columns
        assert 'reflection' in columns
        assert 'profit_loss' in columns
        assert columns['profit_loss'] == 'REAL'

        conn.close()


class TestGetDecisionsWithoutReflection:
    """Test the get_decisions_without_reflection function."""

    def test_returns_empty_list_for_empty_db(self, test_db):
        """Test that function returns empty list when no trades exist."""
        result = get_decisions_without_reflection(db_path=test_db)
        assert result == []

    def test_filters_by_min_hours_old(self, populated_db):
        """Test that function correctly filters by minimum age."""
        # With 24 hour minimum, should return 2 trades (48h and 30h old)
        result = get_decisions_without_reflection(
            min_hours_old=24,
            db_path=populated_db
        )
        assert len(result) == 2

        # With 48 hour minimum, should return 1 trade (only 48h old)
        result = get_decisions_without_reflection(
            min_hours_old=48,
            db_path=populated_db
        )
        assert len(result) == 1

    def test_excludes_trades_with_reflection(self, populated_db):
        """Test that trades with existing reflections are excluded."""
        # Get all trades 24+ hours old
        result = get_decisions_without_reflection(
            min_hours_old=24,
            db_path=populated_db
        )

        # Should not include the BTC trade that has reflection
        coin_names = [r['coin_name'] for r in result]
        assert 'BTC' not in coin_names
        assert all(r['coin_name'] == 'ADA' for r in result)

    def test_filters_by_coin_name(self, populated_db):
        """Test filtering by specific coin."""
        result = get_decisions_without_reflection(
            coin_name="ADA",
            min_hours_old=24,
            db_path=populated_db
        )
        assert all(r['coin_name'] == 'ADA' for r in result)
        assert len(result) == 2

    def test_returns_oldest_first(self, populated_db):
        """Test that results are ordered by timestamp ascending (oldest first)."""
        result = get_decisions_without_reflection(
            min_hours_old=24,
            db_path=populated_db
        )

        # Parse timestamps and verify order
        timestamps = [datetime.fromisoformat(r['timestamp']) for r in result]
        assert timestamps == sorted(timestamps)

    def test_no_min_hours_filter(self, populated_db):
        """Test with no minimum hours filter."""
        result = get_decisions_without_reflection(
            min_hours_old=None,
            db_path=populated_db
        )
        # Should return all trades without reflection (3 ADA trades)
        assert len(result) == 3


class TestUpdateReflection:
    """Test the update_reflection function."""

    def test_updates_all_reflection_fields(self, populated_db):
        """Test that all reflection fields are updated correctly."""
        # Get a trade without reflection
        trades = get_decisions_without_reflection(db_path=populated_db)
        trade_id = trades[0]['id']

        # Update reflection
        reflection_time = datetime.now().isoformat()
        update_reflection(
            record_id=trade_id,
            reflection_timestamp=reflection_time,
            result_type="gain",
            result_description="Price increased 10%",
            reflection="Excellent trade decision based on strong analysis",
            profit_loss=0.10,
            db_path=populated_db
        )

        # Verify update
        conn = sqlite3.connect(populated_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trading_decisions WHERE id = ?", (trade_id,))
        row = dict(cursor.fetchone())
        conn.close()

        assert row['reflection_timestamp'] == reflection_time
        assert row['result_type'] == 'gain'
        assert row['result_description'] == 'Price increased 10%'
        assert row['reflection'] == 'Excellent trade decision based on strong analysis'
        assert row['profit_loss'] == 0.10

    def test_update_with_negative_profit_loss(self, populated_db):
        """Test updating with negative profit/loss."""
        trades = get_decisions_without_reflection(db_path=populated_db)
        trade_id = trades[0]['id']

        update_reflection(
            record_id=trade_id,
            reflection_timestamp=datetime.now().isoformat(),
            result_type="loss",
            result_description="Price decreased 5%",
            reflection="Market moved against the prediction",
            profit_loss=-0.05,
            db_path=populated_db
        )

        # Verify
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("SELECT profit_loss, result_type FROM trading_decisions WHERE id = ?",
                      (trade_id,))
        row = cursor.fetchone()
        conn.close()

        assert row[0] == -0.05
        assert row[1] == 'loss'

    def test_trade_excluded_after_update(self, populated_db):
        """Test that trade is excluded from future queries after reflection update."""
        # Count before
        before = get_decisions_without_reflection(db_path=populated_db)
        count_before = len(before)

        # Update first trade
        trade_id = before[0]['id']
        update_reflection(
            record_id=trade_id,
            reflection_timestamp=datetime.now().isoformat(),
            result_type="neutral",
            result_description="No significant change",
            reflection="Market remained stable",
            profit_loss=0.0,
            db_path=populated_db
        )

        # Count after
        after = get_decisions_without_reflection(db_path=populated_db)
        count_after = len(after)

        assert count_after == count_before - 1
        assert not any(t['id'] == trade_id for t in after)


class TestIntegration:
    """Integration tests for the reflection workflow."""

    def test_complete_reflection_workflow(self, test_db):
        """Test the complete workflow: insert -> query -> update -> verify."""
        # Step 1: Insert a trade
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        record_id = insert_decision(
            decision="buy",
            coin_name="ETH",
            confidence_score=70.0,
            reason="Testing workflow",
            coin_balance=10.0,
            krw_balance=1000000.0,
            coin_avg_buy_price=3000000.0,
            coin_krw_price=3100000.0,
            trade_amount=500000.0,
            is_real_trade=False,
            timestamp=old_time,
            db_path=test_db
        )

        # Step 2: Query for trades without reflection
        trades = get_decisions_without_reflection(min_hours_old=24, db_path=test_db)
        assert len(trades) == 1
        assert trades[0]['id'] == record_id
        assert trades[0]['reflection'] == ''

        # Step 3: Update with reflection
        update_reflection(
            record_id=record_id,
            reflection_timestamp=datetime.now().isoformat(),
            result_type="gain",
            result_description="Successful trade",
            reflection="AI-generated reflection here",
            profit_loss=0.08,
            db_path=test_db
        )

        # Step 4: Verify trade no longer appears in query
        trades_after = get_decisions_without_reflection(min_hours_old=24, db_path=test_db)
        assert len(trades_after) == 0

        # Step 5: Verify reflection data is stored
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trading_decisions WHERE id = ?", (record_id,))
        row = dict(cursor.fetchone())
        conn.close()

        assert row['result_type'] == 'gain'
        assert row['profit_loss'] == 0.08
        assert len(row['reflection']) > 0
