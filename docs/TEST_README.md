# Test Suite Documentation

## Overview

Comprehensive pytest test suite for the Trade Reflection System, covering database operations and reflection analysis functions.

## Test Files

### 1. `src/tests/test_sql_db.py`
Tests for database operations and reflection-related queries.

**Test Classes:**
- `TestDatabaseSchema` - Validates database schema and column structure
- `TestGetDecisionsWithoutReflection` - Tests querying trades needing reflection
- `TestUpdateReflection` - Tests updating reflection fields
- `TestIntegration` - End-to-end database workflow tests

**Coverage:**
- ✅ Database initialization and schema creation
- ✅ Reflection column existence and types
- ✅ Filtering by minimum age (24+ hours)
- ✅ Excluding trades with existing reflections
- ✅ Filtering by coin name
- ✅ Ordering (oldest first)
- ✅ Updating all reflection fields
- ✅ Negative profit/loss handling
- ✅ Complete insert → query → update → verify workflow

### 2. `src/tests/test_reflection.py`
Tests for price data fetching, trade analysis, and AI reflection generation.

**Test Classes:**
- `TestGetFuturePriceData` - Tests fetching future price data
- `TestAnalyzeTradeResult` - Tests trade outcome analysis
- `TestGenerateReflection` - Tests AI reflection generation
- `TestIntegration` - End-to-end reflection workflow tests

**Coverage:**
- ✅ Fetching future price data from Upbit API
- ✅ Handling recent trades with no future data
- ✅ API error handling
- ✅ Average price calculation
- ✅ BUY + price increase = gain
- ✅ BUY + price decrease = loss
- ✅ SELL + price decrease = gain (good timing)
- ✅ SELL + price increase = loss (missed opportunity)
- ✅ HOLD always neutral with 0 profit/loss
- ✅ Small changes (<1%) classified as neutral
- ✅ Profit/loss calculation accuracy
- ✅ OpenAI API integration
- ✅ Error handling for API failures
- ✅ Complete data fetch → analyze → reflect workflow

## Installation

Install test dependencies:

```bash
pip install pytest>=7.0.0 pytest-mock>=3.10.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
cd /Users/tkim9/Documents/git/upbit_mcp
pytest
```

### Run Specific Test File

```bash
# Test database functions
pytest src/tests/test_sql_db.py

# Test reflection functions
pytest src/tests/test_reflection.py
```

### Run Specific Test Class

```bash
pytest src/tests/test_sql_db.py::TestGetDecisionsWithoutReflection
pytest src/tests/test_reflection.py::TestAnalyzeTradeResult
```

### Run Specific Test

```bash
pytest src/tests/test_sql_db.py::TestGetDecisionsWithoutReflection::test_filters_by_min_hours_old
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage Report

```bash
# Install coverage tool
pip install pytest-cov

# Run with coverage
pytest --cov=src/functions --cov-report=html --cov-report=term
```

### Run Only Fast Tests (Skip Slow/API Tests)

```bash
pytest -m "not slow and not api"
```

## Test Fixtures

### Database Fixtures
- `test_db` - Creates temporary test database
- `populated_db` - Database with sample trade data

### Trade Record Fixtures
- `sample_trade_buy` - Sample BUY trade
- `sample_trade_sell` - Sample SELL trade
- `sample_trade_hold` - Sample HOLD trade

### Price Data Fixtures
- `mock_price_data_increasing` - Price data showing upward trend
- `mock_price_data_decreasing` - Price data showing downward trend

## Mocking Strategy

### External Dependencies Mocked
- `pyupbit.get_ohlcv()` - Upbit API calls for price data
- `OpenAI()` - OpenAI API calls for reflection generation

### Why Mock?
- **Speed**: Tests run in milliseconds instead of seconds
- **Reliability**: No dependency on external API availability
- **Cost**: Avoid API charges during testing
- **Isolation**: Test logic independently of external services

## Test Output Example

```bash
$ pytest -v

======================== test session starts =========================
platform darwin -- Python 3.10.x, pytest-7.4.x, pluggy-1.3.x
cachedir: .pytest_cache
rootdir: /Users/tkim9/Documents/git/upbit_mcp
configfile: pytest.ini
testpaths: src/tests
collected 35 items

src/tests/test_sql_db.py::TestDatabaseSchema::test_init_db_creates_table PASSED [ 2%]
src/tests/test_sql_db.py::TestDatabaseSchema::test_reflection_columns_exist PASSED [ 5%]
src/tests/test_sql_db.py::TestGetDecisionsWithoutReflection::test_returns_empty_list_for_empty_db PASSED [ 8%]
src/tests/test_sql_db.py::TestGetDecisionsWithoutReflection::test_filters_by_min_hours_old PASSED [11%]
...
src/tests/test_reflection.py::TestAnalyzeTradeResult::test_buy_with_price_increase_is_gain PASSED [68%]
src/tests/test_reflection.py::TestAnalyzeTradeResult::test_profit_loss_calculation_accuracy PASSED [71%]
...

======================== 35 passed in 2.45s ==========================
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest
```

## Writing New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test Structure

```python
import pytest
from functions.my_module import my_function

@pytest.fixture
def sample_data():
    """Fixture providing sample data."""
    return {'key': 'value'}

class TestMyFunction:
    """Test suite for my_function."""

    def test_basic_functionality(self, sample_data):
        """Test that function works with valid input."""
        result = my_function(sample_data)
        assert result is not None

    def test_error_handling(self):
        """Test that function handles errors gracefully."""
        with pytest.raises(ValueError):
            my_function(None)
```

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError`, ensure you're running pytest from the project root:
```bash
cd /Users/tkim9/Documents/git/upbit_mcp
pytest
```

### Database Lock Errors
If tests fail with database lock errors, ensure no other process is accessing the test database.

### Mock Not Working
Ensure the mock path matches the import path in the module being tested:
```python
# If module imports: from functions.reflection import pyupbit
# Mock should be: @patch('functions.reflection.pyupbit.get_ohlcv')
```

## Test Coverage Goals

Current coverage targets:
- **Database functions**: 100% (all critical paths)
- **Reflection functions**: 95%+ (excluding error edge cases)
- **Overall**: 90%+

## Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Test names should describe what they test
3. **Speed**: Use mocks for external dependencies
4. **Completeness**: Test both success and failure cases
5. **Fixtures**: Reuse test data via fixtures
6. **Assertions**: Use specific assertions with clear messages

## Future Enhancements

Potential test additions:
- [ ] Performance benchmarks
- [ ] Load testing for database operations
- [ ] Integration tests with real API (marked as slow)
- [ ] Property-based testing with hypothesis
- [ ] Mutation testing with mutmut
