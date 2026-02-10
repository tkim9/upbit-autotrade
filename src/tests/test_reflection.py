"""
Pytest tests for reflection module functions.
Tests price data fetching, trade analysis, and reflection generation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from functions.reflection import (
    get_future_price_data,
    analyze_trade_result,
    generate_reflection
)


@pytest.fixture
def sample_trade_buy():
    """Sample BUY trade record."""
    return {
        'id': 1,
        'timestamp': (datetime.now() - timedelta(hours=25)).isoformat(),
        'decision': 'buy',
        'confidence_score': 75.0,
        'reason': 'Strong bullish signal on chart with RSI oversold',
        'coin_name': 'ADA',
        'coin_balance': 1000.0,
        'krw_balance': 500000.0,
        'coin_avg_buy_price': 500.0,
        'coin_krw_price': 1000.0,
        'trade_amount': 100000.0,
        'is_real_trade': 0
    }


@pytest.fixture
def sample_trade_sell():
    """Sample SELL trade record."""
    return {
        'id': 2,
        'timestamp': (datetime.now() - timedelta(hours=30)).isoformat(),
        'decision': 'sell',
        'confidence_score': 60.0,
        'reason': 'Overbought conditions, taking profits',
        'coin_name': 'ADA',
        'coin_balance': 500.0,
        'krw_balance': 800000.0,
        'coin_avg_buy_price': 500.0,
        'coin_krw_price': 1200.0,
        'trade_amount': 500.0,
        'is_real_trade': 0
    }


@pytest.fixture
def sample_trade_hold():
    """Sample HOLD trade record."""
    return {
        'id': 3,
        'timestamp': (datetime.now() - timedelta(hours=26)).isoformat(),
        'decision': 'hold',
        'confidence_score': 0.0,
        'reason': 'Market conditions unclear, waiting for better signal',
        'coin_name': 'ADA',
        'coin_balance': 500.0,
        'krw_balance': 800000.0,
        'coin_avg_buy_price': 500.0,
        'coin_krw_price': 1100.0,
        'trade_amount': 0.0,
        'is_real_trade': 0
    }


@pytest.fixture
def mock_price_data_increasing():
    """Mock price data showing increasing trend.
    - For BUY at 1000: avg 1300 > 1000 = gain (price went up after buying)
    - For SELL at 1200: avg 1300 > 1200 = loss (price went up after selling, missed opportunity)
    """
    base_time = datetime.now() - timedelta(hours=24)
    data = []
    for i in range(24):
        data.append({
            'timestamp': (base_time + timedelta(hours=i)).isoformat(),
            'open': 1100.0 + i * 10,
            'high': 1110.0 + i * 10,
            'low': 1090.0 + i * 10,
            'close': 1105.0 + i * 10,
            'volume': 1000000.0
        })

    return {
        'ohlcv_data': data,
        'hours_available': 24,
        'start_time': data[0]['timestamp'],
        'end_time': data[-1]['timestamp'],
        'avg_price': 1300.0  # > 1200 (SELL price) and > 1000 (BUY price)
    }


@pytest.fixture
def mock_price_data_decreasing():
    """Mock price data showing decreasing trend.
    - For BUY at 1000: avg 950 < 1000 = loss (price went down after buying)
    - For SELL at 1200: avg 950 < 1200 = gain (price went down after selling, good timing)
    """
    base_time = datetime.now() - timedelta(hours=24)
    data = []
    for i in range(24):
        data.append({
            'timestamp': (base_time + timedelta(hours=i)).isoformat(),
            'open': 1000.0 - i * 2,
            'high': 1010.0 - i * 2,
            'low': 990.0 - i * 2,
            'close': 995.0 - i * 2,
            'volume': 1000000.0
        })

    return {
        'ohlcv_data': data,
        'hours_available': 24,
        'start_time': data[0]['timestamp'],
        'end_time': data[-1]['timestamp'],
        'avg_price': 950.0  # < 1000 (BUY price) and < 1200 (SELL price)
    }


class TestGetFuturePriceData:
    """Test the get_future_price_data function."""

    @patch('functions.reflection.pyupbit.get_ohlcv')
    def test_returns_data_for_valid_timestamp(self, mock_get_ohlcv):
        """Test that function returns price data for a valid old timestamp."""
        # Mock pyupbit response
        trade_time = datetime.now() - timedelta(hours=30)

        # Create mock dataframe with hourly data
        dates = pd.date_range(start=trade_time - timedelta(hours=10),
                             end=trade_time + timedelta(hours=30),
                             freq='h')
        mock_df = pd.DataFrame({
            'open': [1000.0] * len(dates),
            'high': [1010.0] * len(dates),
            'low': [990.0] * len(dates),
            'close': [1005.0] * len(dates),
            'volume': [1000000.0] * len(dates)
        }, index=dates)

        mock_get_ohlcv.return_value = mock_df

        result = get_future_price_data('ADA', trade_time.isoformat(), hours=24)

        assert 'ohlcv_data' in result
        assert 'hours_available' in result
        assert 'avg_price' in result
        assert result['hours_available'] > 0
        assert result['avg_price'] is not None

    def test_handles_recent_trade(self):
        """Test handling of very recent trades with no future data."""
        recent_time = (datetime.now() - timedelta(minutes=30)).isoformat()

        result = get_future_price_data('ADA', recent_time, hours=24)

        assert result['hours_available'] == 0
        assert 'error' in result

    @patch('functions.reflection.pyupbit.get_ohlcv')
    def test_handles_api_error(self, mock_get_ohlcv):
        """Test handling of API errors."""
        mock_get_ohlcv.return_value = None

        old_time = (datetime.now() - timedelta(hours=30)).isoformat()
        result = get_future_price_data('ADA', old_time, hours=24)

        assert 'error' in result
        assert result['hours_available'] == 0

    @patch('functions.reflection.pyupbit.get_ohlcv')
    def test_calculates_average_price(self, mock_get_ohlcv):
        """Test that average price is calculated correctly."""
        trade_time = datetime.now() - timedelta(hours=30)

        dates = pd.date_range(start=trade_time + timedelta(hours=1),
                             end=trade_time + timedelta(hours=24),
                             freq='h')
        mock_df = pd.DataFrame({
            'open': [1000.0] * len(dates),
            'high': [1010.0] * len(dates),
            'low': [990.0] * len(dates),
            'close': [1000.0, 1100.0, 1200.0] + [1100.0] * (len(dates) - 3),
            'volume': [1000000.0] * len(dates)
        }, index=dates)

        mock_get_ohlcv.return_value = mock_df

        result = get_future_price_data('ADA', trade_time.isoformat(), hours=24)

        assert result['avg_price'] is not None
        assert isinstance(result['avg_price'], float)


class TestAnalyzeTradeResult:
    """Test the analyze_trade_result function."""

    def test_buy_with_price_increase_is_gain(self, sample_trade_buy, mock_price_data_increasing):
        """Test that BUY followed by price increase is classified as gain."""
        result = analyze_trade_result(sample_trade_buy, mock_price_data_increasing)

        assert result['result_type'] == 'gain'
        assert result['profit_loss'] > 0.01  # > 1%
        assert 'profit' in result['result_description'].lower() or 'increased' in result['result_description'].lower()

    def test_buy_with_price_decrease_is_loss(self, sample_trade_buy, mock_price_data_decreasing):
        """Test that BUY followed by price decrease is classified as loss."""
        result = analyze_trade_result(sample_trade_buy, mock_price_data_decreasing)

        assert result['result_type'] == 'loss'
        assert result['profit_loss'] < -0.01  # < -1%
        assert 'loss' in result['result_description'].lower() or 'decreased' in result['result_description'].lower()

    def test_sell_with_price_decrease_is_gain(self, sample_trade_sell, mock_price_data_decreasing):
        """Test that SELL followed by price decrease is classified as gain (good timing)."""
        result = analyze_trade_result(sample_trade_sell, mock_price_data_decreasing)

        assert result['result_type'] == 'gain'
        assert result['profit_loss'] > 0.01
        assert 'good timing' in result['result_description'].lower() or 'avoided' in result['result_description'].lower()

    def test_sell_with_price_increase_is_loss(self, sample_trade_sell, mock_price_data_increasing):
        """Test that SELL followed by price increase is classified as loss (missed gains)."""
        result = analyze_trade_result(sample_trade_sell, mock_price_data_increasing)

        assert result['result_type'] == 'loss'
        assert result['profit_loss'] < -0.01
        assert 'missed' in result['result_description'].lower()

    def test_hold_always_neutral(self, sample_trade_hold, mock_price_data_increasing):
        """Test that HOLD decisions are always neutral with 0 profit/loss."""
        result = analyze_trade_result(sample_trade_hold, mock_price_data_increasing)

        assert result['result_type'] == 'neutral'
        assert result['profit_loss'] == 0.0
        assert 'hold' in result['result_description'].lower()

    def test_small_price_change_is_neutral(self, sample_trade_buy):
        """Test that small price changes (< 1%) are classified as neutral."""
        # Price data with minimal change
        small_change_data = {
            'ohlcv_data': [],
            'hours_available': 24,
            'avg_price': 1005.0  # Only 0.5% increase from 1000
        }

        result = analyze_trade_result(sample_trade_buy, small_change_data)

        assert result['result_type'] == 'neutral'
        assert -0.01 <= result['profit_loss'] <= 0.01

    def test_handles_missing_price_data(self, sample_trade_buy):
        """Test handling of missing or insufficient price data."""
        no_data = {
            'ohlcv_data': [],
            'hours_available': 0,
            'avg_price': None,
            'error': 'No data available'
        }

        result = analyze_trade_result(sample_trade_buy, no_data)

        assert result['result_type'] == 'neutral'
        assert result['profit_loss'] == 0.0
        assert 'insufficient' in result['result_description'].lower()

    def test_profit_loss_calculation_accuracy(self, sample_trade_buy):
        """Test that profit/loss percentage is calculated correctly."""
        # Trade price: 1000, Future avg: 1100 -> 10% gain
        price_data = {
            'ohlcv_data': [],
            'hours_available': 24,
            'avg_price': 1100.0
        }

        result = analyze_trade_result(sample_trade_buy, price_data)

        expected_profit_loss = (1100.0 - 1000.0) / 1000.0
        assert abs(result['profit_loss'] - expected_profit_loss) < 0.001


class TestGenerateReflection:
    """Test the generate_reflection function."""

    @patch('functions.reflection.OpenAI')
    def test_calls_openai_api(self, mock_openai_class, sample_trade_buy, mock_price_data_increasing):
        """Test that function calls OpenAI API with correct parameters."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_parsed = Mock()
        mock_parsed.reflection = "This was a good trade decision based on technical analysis."
        mock_response.choices = [Mock(message=Mock(parsed=mock_parsed))]
        mock_client.chat.completions.parse.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = generate_reflection(
            trade_record=sample_trade_buy,
            future_price_data=mock_price_data_increasing,
            result_type='gain',
            result_description='Price increased 10%',
            profit_loss=0.10
        )

        assert isinstance(result, str)
        assert len(result) > 0
        mock_client.chat.completions.parse.assert_called_once()

    @patch('functions.reflection.OpenAI')
    def test_includes_trade_context_in_prompt(self, mock_openai_class, sample_trade_buy, mock_price_data_increasing):
        """Test that the prompt includes relevant trade context."""
        mock_client = Mock()
        mock_response = Mock()
        mock_parsed = Mock()
        mock_parsed.reflection = "Reflection text"
        mock_response.choices = [Mock(message=Mock(parsed=mock_parsed))]
        mock_client.chat.completions.parse.return_value = mock_response
        mock_openai_class.return_value = mock_client

        generate_reflection(
            trade_record=sample_trade_buy,
            future_price_data=mock_price_data_increasing,
            result_type='gain',
            result_description='Price increased',
            profit_loss=0.10
        )

        # Get the call arguments
        call_args = mock_client.chat.completions.parse.call_args
        messages = call_args[1]['messages']
        user_message = messages[1]['content']

        # Verify key information is in the prompt
        assert 'ADA' in user_message
        assert 'buy' in user_message.lower()
        assert '75' in user_message or '75.0' in user_message  # confidence score
        assert sample_trade_buy['reason'] in user_message

    @patch('functions.reflection.OpenAI')
    def test_handles_api_error(self, mock_openai_class, sample_trade_buy, mock_price_data_increasing):
        """Test handling of OpenAI API errors."""
        mock_client = Mock()
        mock_client.chat.completions.parse.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        result = generate_reflection(
            trade_record=sample_trade_buy,
            future_price_data=mock_price_data_increasing,
            result_type='gain',
            result_description='Price increased',
            profit_loss=0.10
        )

        assert 'error' in result.lower()

    @patch('functions.reflection.OpenAI')
    def test_different_result_types(self, mock_openai_class, sample_trade_buy, mock_price_data_increasing):
        """Test that function works with different result types."""
        mock_client = Mock()
        mock_response = Mock()
        mock_parsed = Mock()
        mock_parsed.reflection = "Reflection"
        mock_response.choices = [Mock(message=Mock(parsed=mock_parsed))]
        mock_client.chat.completions.parse.return_value = mock_response
        mock_openai_class.return_value = mock_client

        for result_type in ['gain', 'loss', 'neutral']:
            result = generate_reflection(
                trade_record=sample_trade_buy,
                future_price_data=mock_price_data_increasing,
                result_type=result_type,
                result_description=f'Test {result_type}',
                profit_loss=0.05 if result_type == 'gain' else -0.05
            )

            assert isinstance(result, str)
            assert len(result) > 0


class TestIntegration:
    """Integration tests for the complete reflection workflow."""

    @patch('functions.reflection.pyupbit.get_ohlcv')
    @patch('functions.reflection.OpenAI')
    def test_complete_reflection_flow(self, mock_openai_class, mock_get_ohlcv, sample_trade_buy):
        """Test the complete flow: fetch data -> analyze -> generate reflection."""
        # Mock price data
        trade_time = datetime.fromisoformat(sample_trade_buy['timestamp'])
        dates = pd.date_range(start=trade_time + timedelta(hours=1),
                             end=trade_time + timedelta(hours=24),
                             freq='h')
        mock_df = pd.DataFrame({
            'open': [1000.0] * len(dates),
            'high': [1010.0] * len(dates),
            'low': [990.0] * len(dates),
            'close': [1100.0] * len(dates),
            'volume': [1000000.0] * len(dates)
        }, index=dates)
        mock_get_ohlcv.return_value = mock_df

        # Mock OpenAI
        mock_client = Mock()
        mock_response = Mock()
        mock_parsed = Mock()
        mock_parsed.reflection = "Excellent trade decision with good timing."
        mock_response.choices = [Mock(message=Mock(parsed=mock_parsed))]
        mock_client.chat.completions.parse.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Step 1: Get future price data
        future_data = get_future_price_data(
            coin_name=sample_trade_buy['coin_name'],
            timestamp=sample_trade_buy['timestamp'],
            hours=24
        )
        assert future_data['hours_available'] > 0

        # Step 2: Analyze trade result
        analysis = analyze_trade_result(sample_trade_buy, future_data)
        assert analysis['result_type'] in ['gain', 'loss', 'neutral']
        assert isinstance(analysis['profit_loss'], float)

        # Step 3: Generate reflection
        reflection = generate_reflection(
            trade_record=sample_trade_buy,
            future_price_data=future_data,
            result_type=analysis['result_type'],
            result_description=analysis['result_description'],
            profit_loss=analysis['profit_loss']
        )
        assert isinstance(reflection, str)
        assert len(reflection) > 0
