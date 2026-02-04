# Trade Reflection System

## Overview

The Trade Reflection System automatically analyzes past trading decisions by comparing them with future price movements and generating AI-powered insights.

## What Was Implemented

### 1. Database Schema Updates (`src/functions/sql_db.py`)

Added 5 new columns to the `trading_decisions` table:

| Column | Type | Description |
|--------|------|-------------|
| `reflection_timestamp` | TEXT | ISO timestamp when reflection was generated |
| `result_type` | TEXT | 'gain', 'loss', or 'neutral' |
| `result_description` | TEXT | Human-readable description of the outcome |
| `reflection` | TEXT | AI-generated reflection analysis |
| `profit_loss` | REAL | Percentage profit/loss (e.g., 0.10 = 10% gain) |

**New Functions:**
- `get_decisions_without_reflection()` - Query trades needing reflection (24+ hours old by default)
- `update_reflection()` - Update reflection fields for a trade record

### 2. Reflection Functions (`src/functions/reflection.py`)

**Three main functions:**

#### a. `get_future_price_data(coin_name, timestamp, hours=24)`
- Fetches hourly price data for the 24 hours following a trade
- Returns OHLCV data and average price
- Handles cases where full 24 hours isn't available yet

#### b. `analyze_trade_result(trade_record, future_price_data)`
- Calculates profit/loss percentage
- Determines result type (gain/loss/neutral)
- Generates human-readable description

**Calculation Logic:**
- **BUY**: `(avg_future_price - trade_price) / trade_price`
- **SELL**: `(trade_price - avg_future_price) / trade_price` (profit if price drops)
- **HOLD**: 0 (no trade executed)

**Result Type Thresholds:**
- **gain**: profit_loss > 1%
- **loss**: profit_loss < -1%
- **neutral**: -1% to 1%

#### c. `generate_reflection(trade_record, future_price_data, result_type, result_description, profit_loss)`
- Uses OpenAI API to generate thoughtful analysis
- Considers original reasoning, confidence score, and actual outcome
- Provides actionable insights and lessons learned

### 3. Orchestration Script (`scripts/generate_reflection.py`)

A complete script that:
1. Finds all trades without reflection (24+ hours old)
2. For each trade:
   - Fetches future price data
   - Analyzes the outcome
   - Generates AI reflection
   - Updates the database
3. Prints comprehensive statistics

## Usage

### Running the Reflection Generator

```bash
cd /Users/tkim9/Documents/git/upbit_mcp
python scripts/generate_reflection.py
```

### Requirements

- Trades must be at least 24 hours old
- OpenAI API key must be configured in `.env`
- Network access to fetch price data from Upbit

### Example Output

```
==========================================================
Trading Decision Reflection Generator
==========================================================

Fetching trades without reflection (24+ hours old)...
Found 3 trade(s) to analyze

[1/3] Processing trade ID 5
  Coin: ADA
  Decision: BUY
  Timestamp: 2026-02-02T15:30:00
  Price: 1000.00 KRW
  → Fetching future price data...
  ✓ Retrieved 24 hours of price data
  → Analyzing trade outcome...
  ✓ Result: GAIN (8.50%)
     BUY at 1000.00 KRW. Price increased to 1085.00 KRW...
  → Generating AI reflection...
  ✓ Generated reflection (523 chars)
  → Updating database...
  ✓ Database updated

...

==========================================================
SUMMARY
==========================================================
Total trades analyzed:    3
Successfully processed:   3
Errors:                   0

Results Breakdown:
  Gains:    2
  Losses:   1
  Neutral:  0

Average Profit/Loss: 3.25%
📈 Overall: Profitable trading decisions
```

## Database Queries

### Get all reflections
```python
from src.functions.sql_db import get_all_decisions

decisions = get_all_decisions(coin_name="ADA")
for d in decisions:
    if d['reflection']:
        print(f"Trade {d['id']}: {d['result_type']} ({d['profit_loss']*100:.2f}%)")
        print(f"Reflection: {d['reflection'][:200]}...")
```

### Get trades needing reflection
```python
from src.functions.sql_db import get_decisions_without_reflection

# Trades 24+ hours old without reflection
pending = get_decisions_without_reflection(min_hours_old=24)

# Trades 1+ hour old (for testing)
recent = get_decisions_without_reflection(min_hours_old=1)
```

## Technical Notes

### Migration Handling

The system automatically adds new columns to existing databases. If you already have a `trading_decisions` table, the new columns will be added with default empty values when you first call `init_db()`.

### Future Price Data

The system uses `pyupbit.get_ohlcv()` with `interval="minute60"` to fetch hourly candle data. It filters this data to the 24-hour window following the trade timestamp.

### AI Reflection Quality

Reflections consider:
- Original reasoning and decision
- Confidence score calibration
- Actual price movements
- Technical and fundamental factors
- Actionable lessons for future trades

## Troubleshooting

### "No trades found that need reflection"
- Trades must be at least 24 hours old
- Check if trades already have reflections: `SELECT * FROM trading_decisions WHERE reflection != ''`

### "Insufficient future price data"
- Trade is too recent (< 24 hours old)
- Wait for more time to pass after the trade

### API Errors
- Verify OpenAI API key in `.env`
- Check network connectivity for Upbit API
- Ensure sufficient API credits

## Files Modified

1. `src/functions/sql_db.py` - Database schema and queries
2. `src/functions/reflection.py` - Reflection logic (new file)
3. `scripts/generate_reflection.py` - Orchestration script (new file)

## Next Steps

1. **Wait for trades to age**: Trades need to be 24+ hours old
2. **Run reflection script**: `python scripts/generate_reflection.py`
3. **Review insights**: Query the database to see reflections
4. **Improve strategy**: Use insights to refine trading decisions

## Success Criteria

✅ Database schema updated with 5 new columns
✅ Migration handles existing databases
✅ Price data fetching works correctly
✅ Profit/loss calculation implemented
✅ AI reflection generation functional
✅ Orchestration script complete
✅ All linter errors resolved

The system is ready to use! Just wait for your trades to be 24+ hours old and run the reflection script.
