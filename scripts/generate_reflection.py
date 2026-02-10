"""
Script to generate reflections for past trading decisions.

This script:
1. Fetches all trades without reflection that are at least 24 hours old
2. For each trade, fetches 24h future price data
3. Analyzes the outcome (gain/loss/neutral)
4. Generates AI-powered reflection
5. Updates the database with reflection data
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import after path modification (required for project structure)
from src.functions.sql_db import get_decisions_without_reflection, update_reflection  # noqa: E402
from src.functions.reflection import get_future_price_data, analyze_trade_result, generate_reflection  # noqa: E402

# Load environment variables
load_dotenv()


def main():
    """Main function to generate reflections for trades."""
    print("=" * 60)
    print("Trading Decision Reflection Generator")
    print("=" * 60)
    print()

    # Get all trades without reflection (at least 24 hours old)
    print("Fetching trades without reflection (24+ hours old)...")
    trades = get_decisions_without_reflection(min_hours_old=24)

    if not trades:
        print("✓ No trades found that need reflection. All caught up!")
        return

    print(f"Found {len(trades)} trade(s) to analyze")
    print()

    # Track statistics
    stats = {
        'total': len(trades),
        'processed': 0,
        'gains': 0,
        'losses': 0,
        'neutral': 0,
        'errors': 0,
        'total_profit_loss': 0.0
    }

    # Process each trade
    for i, trade in enumerate(trades, 1):
        print(f"\n[{i}/{len(trades)}] Processing trade ID {trade['id']}")
        print(f"  Coin: {trade['coin_name']}")
        print(f"  Decision: {trade['decision'].upper()}")
        print(f"  Timestamp: {trade['timestamp']}")
        print(f"  Price: {trade['coin_krw_price']:.2f} KRW")

        try:
            # Step 1: Fetch future price data
            print("  → Fetching future price data...")
            future_price_data = get_future_price_data(
                coin_name=trade['coin_name'],
                timestamp=trade['timestamp'],
                hours=24
            )

            if future_price_data.get('error'):
                print(f"  ✗ Error: {future_price_data['error']}")
                stats['errors'] += 1
                continue

            hours_available = future_price_data.get('hours_available', 0)
            print(f"  ✓ Retrieved {hours_available} hours of price data")

            if hours_available < 12:
                print(f"  ⚠ Warning: Only {hours_available} hours available (minimum 12 recommended)")

            # Step 2: Analyze trade result
            print("  → Analyzing trade outcome...")
            analysis = analyze_trade_result(trade, future_price_data)

            result_type = analysis['result_type']
            result_description = analysis['result_description']
            profit_loss = analysis['profit_loss']

            print(f"  ✓ Result: {result_type.upper()} ({profit_loss*100:.2f}%)")
            print(f"     {result_description}")

            # Step 3: Generate AI reflection
            print("  → Generating AI reflection...")
            reflection_text = generate_reflection(
                trade_record=trade,
                future_price_data=future_price_data,
                result_type=result_type,
                result_description=result_description,
                profit_loss=profit_loss
            )

            if reflection_text.startswith("Error"):
                print(f"  ✗ {reflection_text}")
                stats['errors'] += 1
                continue

            print(f"  ✓ Generated reflection ({len(reflection_text)} chars)")

            # Step 4: Update database
            print("  → Updating database...")
            reflection_timestamp = datetime.now().isoformat()
            update_reflection(
                record_id=trade['id'],
                reflection_timestamp=reflection_timestamp,
                result_type=result_type,
                result_description=result_description,
                reflection=reflection_text,
                profit_loss=profit_loss
            )
            print("  ✓ Database updated")

            # Update statistics
            stats['processed'] += 1
            stats['total_profit_loss'] += profit_loss
            if result_type == 'gain':
                stats['gains'] += 1
            elif result_type == 'loss':
                stats['losses'] += 1
            else:
                stats['neutral'] += 1

        except Exception as e:
            print(f"  ✗ Unexpected error: {str(e)}")
            stats['errors'] += 1
            import traceback
            traceback.print_exc()

    # Print summary statistics
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total trades analyzed:    {stats['total']}")
    print(f"Successfully processed:   {stats['processed']}")
    print(f"Errors:                   {stats['errors']}")
    print()
    print("Results Breakdown:")
    print(f"  Gains:    {stats['gains']}")
    print(f"  Losses:   {stats['losses']}")
    print(f"  Neutral:  {stats['neutral']}")
    print()

    if stats['processed'] > 0:
        avg_profit_loss = stats['total_profit_loss'] / stats['processed']
        print(f"Average Profit/Loss: {avg_profit_loss*100:.2f}%")

        if avg_profit_loss > 0:
            print("📈 Overall: Profitable trading decisions")
        elif avg_profit_loss < 0:
            print("📉 Overall: Losing trading decisions")
        else:
            print("➡️  Overall: Break-even trading decisions")

    print()
    print("=" * 60)
    print("✓ Reflection generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
