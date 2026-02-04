import os
import sys
from dotenv import load_dotenv
import ta
import base64
from datetime import datetime
from pydantic import BaseModel
from typing import Literal

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import from new locations
from functions.fg_index import get_fear_greed_index
from functions.news import get_news_sentiment_summary
from functions.chart_img import take_full_page_screenshot
from functions.sql_db import insert_decision

load_dotenv()
TRADE_ON = False

def add_indicators(df):
    # bollinger bands
    indicator_bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_bbm'] = indicator_bb.bollinger_mavg()
    df['bb_bbhi'] = indicator_bb.bollinger_hband()
    df['bb_bbli'] = indicator_bb.bollinger_lband()

    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

    # MACD
    df['macd'] = ta.trend.MACD(df['close']).macd()
    df['macd_signal'] = ta.trend.MACD(df['close']).macd_signal()
    df['macd_diff'] = ta.trend.MACD(df['close']).macd_diff()

    # moving average of 20, 12
    df['sma20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
    df['ema12'] = ta.trend.EMAIndicator(df['close'], window=12).ema_indicator()

    return df

class TradingDecision(BaseModel):
    """Structured output for trading decision"""
    reason: str
    decision: Literal["buy", "sell", "hold"]
    confidence_score: int  # 0 if hold, 0-100 if buy or sell

def ai_trading():
    # Get project root for file paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # 1. get upbit chart data - both daily and hourly
    import pyupbit

    access = os.getenv("UPBIT_OPEN_API_ACCESS_KEY")
    secret = os.getenv("UPBIT_OPEN_API_SECRET_KEY")
    upbit = pyupbit.Upbit(access, secret)
    coin = "ADA"
    trading_fee = 0.0005

    # get balances
    all_balances = upbit.get_balances()
    coin_to_watch = ["ADA", "KRW"]
    filtered_balances = [balance for balance in all_balances if balance["currency"] in coin_to_watch]
    print(f"balances: {filtered_balances}")

    # orderbook price
    orderbook = pyupbit.get_orderbook(f"KRW-{coin}")
    print(f"orderbook: {orderbook}")

    # Get 30 days of daily data
    df_daily = pyupbit.get_ohlcv(f"KRW-{coin}", interval="day", count=30)
    df_daily = add_indicators(df_daily)
    print(f"Daily data shape: {df_daily.shape}")

    # Get 24 hours of hourly data (24 * 1 = 24 hours)
    df_hourly = pyupbit.get_ohlcv(f"KRW-{coin}", interval="minute60", count=24)
    df_hourly = add_indicators(df_hourly)
    print(f"Hourly data shape: {df_hourly.shape}")

    # Convert to JSON format for AI analysis
    daily_data = df_daily.to_json(orient="records")
    hourly_data = df_hourly.to_json(orient="records")
    fg_index_data = get_fear_greed_index(limit=30, date_format='us')

    # get news sentiment summary
    news_summary = get_news_sentiment_summary(query="ADA cryptocurrency news", time_period="qdr:d", num=10)
    print(f"News summary: {news_summary}")

    # Read trading strategy (from project root)
    strategy_path = os.path.join(project_root, "strategy", "strategy_20260125.md")
    try:
        with open(strategy_path, "r", encoding="utf-8") as f:
            trading_strategy = f.read()
        print(f"Trading strategy loaded from {strategy_path}")
    except Exception as e:
        print(f"Warning: Could not load trading strategy: {e}")
        trading_strategy = ""

    # Capture chart image
    print("Capturing chart image...")
    chart_url = f"https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-{coin}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Ensure charts directory exists (in project root)
    charts_dir = os.path.join(project_root, "charts")
    os.makedirs(charts_dir, exist_ok=True)
    chart_image_path = os.path.join(charts_dir, f"upbit_chart_{coin}_{timestamp}.png")
    try:
        chart_image_path = take_full_page_screenshot(
            url=chart_url,
            output_filename=chart_image_path
        )
        print(f"Chart image captured: {chart_image_path}")

        # Encode image to base64
        with open(chart_image_path, "rb") as image_file:
            chart_image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Warning: Could not capture chart image: {e}")
        chart_image_base64 = None

    # 2. give multi-timeframe data to ai and get suggestions
    from openai import OpenAI

    client = OpenAI()

    # Build user content with text and optional image
    user_content = [
        {
            "type": "text",
            "text": f"""Current investment portfolio:\n{filtered_balances}

            Orderbook price:\n{orderbook}

            ### DATA
            Daily data:\n{daily_data}

            Hourly data:\n{hourly_data}

            Fear and Greed Index data:\n{fg_index_data}

            News summary:\n{news_summary}"""
        }
    ]

    # Add image if available
    if chart_image_base64:
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{chart_image_base64}"
            }
        })

    response = client.chat.completions.parse(
        model="gpt-4o-2024-08-06",  # Using gpt-4o-2024-08-06 which supports structured outputs
        messages=[
            {
                "role": "system",
                "content": f"""You are a ADA coin investing expert following a proven trading strategy. Tell the user whether to buy, sell or hold at the moment based on the input data provided by user and the trading strategy below.

            === TRADING STRATEGY ===
            {trading_strategy}

            === INPUT DATA EXPLANATION ===
            - Current investment portfolio: includes currency, balance, locked
            - Orderbook price: includes current price and bid/ask price
            - Daily data: includes ohlcv, bollinger bands, rsi, macd, macd_signal, macd_diff, sma20, ema12
            - Hourly data: includes ohlcv, bollinger bands, rsi, macd, macd_signal, macd_diff, sma20, ema12
            - Fear and Greed Index data: includes value, value_classification, timestamp, time_until_update
            - Chart image: visual representation of the price chart with technical indicators (Bollinger Bands) and 1-hour timeframe

            === ANALYSIS INSTRUCTIONS ===
            You MUST analyze the data according to the trading strategy principles above. Key points to follow:
            1. **Chart-Based Trading**: Prioritize technical chart analysis over news-driven trades. Focus on chart patterns, support/resistance levels, and market psychology visible in the chart image.
            2. **Risk Management**: Consider the strategy's risk management rules (20-30% of capital per trade, conservative approach).
            3. **Technical Analysis**: While the data includes complex indicators (MACD, RSI, Bollinger Bands), the strategy emphasizes basic chart analysis and market psychology. Use the chart image as the primary source for visual patterns, candlestick formations, and trend identification. Use the technical indicators as supplementary information, not as primary decision drivers.
            4. **Market Conditions**: Assess whether the market shows clear trends (bullish or bearish) as required by the strategy.
            5. **Entry/Exit Rules**: Apply the strategy's entry and exit rules based on chart patterns and support/resistance levels.

            You should consider the current investment portfolio, orderbook price, daily data, hourly data, fear and greed index data, and the chart image to make a decision. Analyze the chart image for visual patterns, support/resistance levels, and market psychology. Think about each data point and go through them in the reasoning process according to the trading strategy. Then make decision based on the data, the strategy principles, and the reasoning process.

            === OUTPUT FORMAT ===
            Provide your reasoning in the 'reason' field, your decision (buy, sell, or hold) in the 'decision' field, and a confidence_score (0-100 integer) in the 'confidence_score' field.

            In the 'reason' field, you MUST:
            - Explicitly reference which aspects of the trading strategy you are applying
            - Explain how the chart analysis aligns with the strategy's principles
            - Describe how you're using the data according to the strategy (e.g., focusing on chart patterns over complex indicators, considering risk management rules, etc.)
            - Justify your decision based on the strategy's entry/exit rules and market condition assessment

            Confidence score rules:
            - If decision is 'hold', confidence_score must be 0
            - If decision is 'buy' or 'sell', confidence_score should be an integer between 0 and 100 representing your confidence level (0 = no confidence, 100 = maximum confidence)
            - Consider the strategy's emphasis on conservative, disciplined trading when setting confidence scores"""
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        response_format=TradingDecision
    )
    result = response.choices[0].message.parsed
    print(f"Reason: {result.reason}")
    print(f"Decision: {result.decision}")
    print(f"Confidence Score: {result.confidence_score}")

    # 3. execute the decision
    current_cash = upbit.get_balance("KRW")
    current_ada = upbit.get_balance(coin)

    print(f'Current cash: {current_cash}')
    print(f'Current ADA: {current_ada}')

    # Get current price and average buy price
    current_price = pyupbit.get_current_price(f"KRW-{coin}")

    # Get average buy price from balance data
    coin_avg_buy_price = None
    for balance in filtered_balances:
        if balance["currency"] == coin:
            avg_buy_price = balance.get("avg_buy_price")
            if avg_buy_price:
                coin_avg_buy_price = float(avg_buy_price)
            break

    # Track trade amount for logging
    trade_amount = None

    if TRADE_ON:
        # Convert confidence_score to decimal (0-100 -> 0.0-1.0)
        confidence_decimal = result.confidence_score / 100.0

        if result.decision == "buy":
            print("Executing BUY order...")
            my_krw = current_cash
            # Apply confidence_score to the trade volume
            trade_amount_krw = my_krw * confidence_decimal * (1 - trading_fee)
            if trade_amount_krw > 5000:
                try:
                    order_result = upbit.buy_market_order("KRW-ADA", trade_amount_krw)
                    print(f"Buy order result: {order_result}")
                    print(f"Traded {confidence_decimal * 100:.1f}% of available cash ({trade_amount_krw:.0f} KRW)")
                    trade_amount = trade_amount_krw  # Store KRW amount for buy
                except Exception as e:
                    print(f"Buy order failed: {e}")
            else:
                print(f"Not enough KRW after applying confidence score (minimum 5000 KRW required, got {trade_amount_krw:.0f} KRW)")

        elif result.decision == "sell":
            print("Executing SELL order...")
            my_ada = current_ada
            # Apply confidence_score to the trade volume
            ada_to_sell = my_ada * confidence_decimal
            current_price = pyupbit.get_orderbook(ticker="KRW-ADA")["orderbook_units"][0]["ask_price"]

            if ada_to_sell and ada_to_sell * current_price * (1 - trading_fee) > 5000:
                try:
                    order_result = upbit.sell_market_order("KRW-ADA", ada_to_sell)
                    print(f"Sell order result: {order_result}")
                    print(f"Traded {confidence_decimal * 100:.1f}% of available ADA ({ada_to_sell:.6f} ADA)")
                    trade_amount = ada_to_sell  # Store coin amount for sell
                except Exception as e:
                    print(f"Sell order failed: {e}")
            else:
                print("Not enough ADA after applying confidence score or order value too small (minimum 5000 KRW)")
        else:
            print("HOLDING - No action taken")
            trade_amount = 0  # Set trade_amount to 0 for hold decisions

    # Get final balances after trade execution
    final_cash = upbit.get_balance("KRW")
    final_ada = upbit.get_balance(coin)

    # Get updated average buy price after trade
    all_balances_after = upbit.get_balances()
    coin_avg_buy_price_after = None
    for balance in all_balances_after:
        if balance["currency"] == coin:
            avg_buy_price = balance.get("avg_buy_price")
            if avg_buy_price:
                coin_avg_buy_price_after = float(avg_buy_price)
            break

    # Get current price for final logging
    final_price = pyupbit.get_current_price(f"KRW-{coin}")

    # Log the trading decision to database (after trade execution)
    try:
        record_id = insert_decision(
            decision=result.decision,
            coin_name=coin,
            confidence_score=float(result.confidence_score),
            reason=result.reason,
            coin_balance=final_ada if final_ada else None,
            krw_balance=final_cash if final_cash else None,
            coin_avg_buy_price=coin_avg_buy_price_after if coin_avg_buy_price_after else coin_avg_buy_price,
            coin_krw_price=final_price if final_price else current_price,
            trade_amount=trade_amount,
            is_real_trade=TRADE_ON
        )
        print(f"Trading decision logged to database with ID: {record_id}")
    except Exception as e:
        print(f"Warning: Failed to log trading decision to database: {e}")

if __name__ == "__main__":
    ai_trading()
