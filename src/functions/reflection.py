import pyupbit
from datetime import datetime, timedelta
from typing import Dict, Any
from openai import OpenAI
from pydantic import BaseModel


def get_future_price_data(coin_name: str, timestamp: str, hours: int = 24) -> Dict[str, Any]:
    """
    Get future price data for a coin starting from a given timestamp.

    Args:
        coin_name: Name of the cryptocurrency (e.g., 'ADA')
        timestamp: ISO format timestamp of the trade
        hours: Number of hours of future data to fetch (default 24)

    Returns:
        Dictionary containing:
        - ohlcv_data: List of OHLCV records
        - hours_available: Number of hours of data actually retrieved
        - start_time: Start timestamp
        - end_time: End timestamp
        - avg_price: Average closing price over the period
    """
    # Parse the trade timestamp
    trade_time = datetime.fromisoformat(timestamp)
    current_time = datetime.now()

    # Calculate how many hours of future data are actually available
    hours_since_trade = (current_time - trade_time).total_seconds() / 3600
    hours_available = min(hours, int(hours_since_trade))

    if hours_available < 1:
        return {
            'ohlcv_data': [],
            'hours_available': 0,
            'start_time': timestamp,
            'end_time': timestamp,
            'avg_price': None,
            'error': 'Trade is too recent, no future data available'
        }

    try:
        # Fetch hourly OHLCV data
        # pyupbit.get_ohlcv returns recent data, so we need to get enough data
        # and then filter to the time range we want
        df = pyupbit.get_ohlcv(f"KRW-{coin_name}", interval="minute60", count=200)

        if df is None or df.empty:
            return {
                'ohlcv_data': [],
                'hours_available': 0,
                'start_time': timestamp,
                'end_time': timestamp,
                'avg_price': None,
                'error': 'No price data available'
            }

        # Filter data to the future window (from trade_time to trade_time + hours)
        end_time = trade_time + timedelta(hours=hours)

        # Filter dataframe to only include data in our time range
        mask = (df.index > trade_time) & (df.index <= end_time)
        df_filtered = df[mask]

        if df_filtered.empty:
            return {
                'ohlcv_data': [],
                'hours_available': 0,
                'start_time': timestamp,
                'end_time': timestamp,
                'avg_price': None,
                'error': 'No data in the specified time range'
            }

        # Calculate average price
        avg_price = df_filtered['close'].mean()

        # Convert to JSON-serializable format
        ohlcv_data = []
        for idx, row in df_filtered.iterrows():
            ohlcv_data.append({
                'timestamp': idx.isoformat(),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })

        return {
            'ohlcv_data': ohlcv_data,
            'hours_available': len(ohlcv_data),
            'start_time': ohlcv_data[0]['timestamp'] if ohlcv_data else timestamp,
            'end_time': ohlcv_data[-1]['timestamp'] if ohlcv_data else timestamp,
            'avg_price': float(avg_price)
        }

    except Exception as e:
        return {
            'ohlcv_data': [],
            'hours_available': 0,
            'start_time': timestamp,
            'end_time': timestamp,
            'avg_price': None,
            'error': f'Error fetching price data: {str(e)}'
        }


def analyze_trade_result(trade_record: Dict[str, Any], future_price_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the outcome of a trade decision based on future price movements.

    Args:
        trade_record: Dictionary containing the trade decision record
        future_price_data: Dictionary containing future price data from get_future_price_data()

    Returns:
        Dictionary containing:
        - result_type: 'gain', 'loss', or 'neutral'
        - result_description: Text description of the outcome
        - profit_loss: Percentage profit/loss as decimal (e.g., 0.10 for 10%)
    """
    decision = trade_record['decision']
    trade_price = trade_record['coin_krw_price']
    avg_future_price = future_price_data.get('avg_price')
    hours_available = future_price_data.get('hours_available', 0)

    # Handle case where no future data is available
    if avg_future_price is None or hours_available == 0:
        return {
            'result_type': 'neutral',
            'result_description': 'Insufficient future price data to analyze outcome',
            'profit_loss': 0.0
        }

    # Calculate profit/loss based on decision type
    if decision.lower() == 'hold':
        profit_loss = 0.0
        result_description = f"HOLD decision. Price moved from {trade_price:.2f} to {avg_future_price:.2f} KRW (avg over {hours_available}h). No trade executed."
        result_type = 'neutral'

    elif decision.lower() == 'buy':
        # For BUY: profit if price goes up
        profit_loss = (avg_future_price - trade_price) / trade_price
        price_change_pct = profit_loss * 100

        if profit_loss > 0.01:  # > 1% gain
            result_type = 'gain'
            result_description = f"BUY at {trade_price:.2f} KRW. Price increased to {avg_future_price:.2f} KRW (avg over {hours_available}h). Profit: {price_change_pct:.2f}%"
        elif profit_loss < -0.01:  # < -1% loss
            result_type = 'loss'
            result_description = f"BUY at {trade_price:.2f} KRW. Price decreased to {avg_future_price:.2f} KRW (avg over {hours_available}h). Loss: {price_change_pct:.2f}%"
        else:
            result_type = 'neutral'
            result_description = f"BUY at {trade_price:.2f} KRW. Price remained stable at {avg_future_price:.2f} KRW (avg over {hours_available}h). Change: {price_change_pct:.2f}%"

    elif decision.lower() == 'sell':
        # For SELL: profit if price goes down (you sold before the drop)
        profit_loss = (trade_price - avg_future_price) / trade_price
        price_change_pct = -profit_loss * 100  # Show actual price movement

        if profit_loss > 0.01:  # > 1% gain (price dropped after selling)
            result_type = 'gain'
            result_description = f"SELL at {trade_price:.2f} KRW. Price dropped to {avg_future_price:.2f} KRW (avg over {hours_available}h). Good timing, avoided {abs(price_change_pct):.2f}% drop"
        elif profit_loss < -0.01:  # < -1% loss (price rose after selling)
            result_type = 'loss'
            result_description = f"SELL at {trade_price:.2f} KRW. Price rose to {avg_future_price:.2f} KRW (avg over {hours_available}h). Missed {price_change_pct:.2f}% gain"
        else:
            result_type = 'neutral'
            result_description = f"SELL at {trade_price:.2f} KRW. Price remained stable at {avg_future_price:.2f} KRW (avg over {hours_available}h). Change: {price_change_pct:.2f}%"

    else:
        # Unknown decision type
        profit_loss = 0.0
        result_type = 'neutral'
        result_description = f"Unknown decision type: {decision}"

    return {
        'result_type': result_type,
        'result_description': result_description,
        'profit_loss': profit_loss
    }


class ReflectionOutput(BaseModel):
    """Structured output for reflection generation"""
    reflection: str


def generate_reflection(
    trade_record: Dict[str, Any],
    future_price_data: Dict[str, Any],
    result_type: str,
    result_description: str,
    profit_loss: float
) -> str:
    """
    Generate AI-powered reflection on a trade decision.

    Args:
        trade_record: Dictionary containing the original trade decision
        future_price_data: Dictionary containing future price data
        result_type: Type of result ('gain', 'loss', 'neutral')
        result_description: Description of the outcome
        profit_loss: Percentage profit/loss as decimal

    Returns:
        Reflection text analyzing what went right or wrong
    """
    client = OpenAI()

    # Prepare the context
    decision = trade_record['decision']
    reason = trade_record['reason']
    confidence_score = trade_record.get('confidence_score', 0)
    coin_name = trade_record['coin_name']
    trade_price = trade_record['coin_krw_price']
    timestamp = trade_record['timestamp']

    # Format future price data for readability
    ohlcv_summary = ""
    if future_price_data.get('ohlcv_data'):
        ohlcv_list = future_price_data['ohlcv_data']
        ohlcv_summary = f"\nPrice movement over {len(ohlcv_list)} hours:"
        for i, data in enumerate(ohlcv_list[:5]):  # Show first 5 hours
            ohlcv_summary += f"\n  Hour {i+1}: Close {data['close']:.2f} KRW"
        if len(ohlcv_list) > 5:
            ohlcv_summary += f"\n  ... ({len(ohlcv_list) - 5} more hours)"

    prompt = f"""You are an expert trading analyst reviewing a past trading decision. Provide a thoughtful reflection on what happened.

### Original Trade Decision
- Coin: {coin_name}
- Decision: {decision.upper()}
- Trade Price: {trade_price:.2f} KRW
- Confidence Score: {confidence_score}%
- Timestamp: {timestamp}
- Reasoning: {reason}

### What Actually Happened
- Result: {result_type.upper()}
- Profit/Loss: {profit_loss*100:.2f}%
- Description: {result_description}
{ohlcv_summary}

### Your Task
Reflect on this trade decision. Consider:
1. **Decision Quality**: Was the reasoning sound? Did it align with good trading principles?
2. **Outcome Analysis**: What factors led to this outcome? Were there signals that were correctly identified or missed?
3. **Confidence Calibration**: Was the confidence score appropriate given the market conditions?
4. **Key Lessons**: What can be learned from this trade for future decisions?

Be specific, analytical, and constructive. Focus on actionable insights."""

    try:
        response = client.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert cryptocurrency trading analyst. Provide thoughtful, analytical reflections on trading decisions. Be specific about what worked and what didn't, and extract actionable lessons."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format=ReflectionOutput
        )

        result = response.choices[0].message.parsed
        return result.reflection

    except Exception as e:
        return f"Error generating reflection: {str(e)}"
