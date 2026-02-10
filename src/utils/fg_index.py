import requests
from typing import Optional, Union, Dict, List
import pandas as pd


def get_fear_greed_index(
    limit: int = 1,
    format_type: str = 'json',
    date_format: str = ''
) -> Union[Dict, str]:
    """
    Get the Fear and Greed Index data from alternative.me API.

    Source: https://alternative.me/crypto/fear-and-greed-index/

    Parameters:
    -----------
    limit : int, optional (default=1)
        Limit the number of returned results.
        - Use 1 for the latest value only
        - Use 0 for all available data
        - Use any positive integer for specific number of results
        Note: "time_until_update" is only returned when limit=1

    format_type : str, optional (default='json')
        Output format: 'json' or 'csv'
        - 'json': Returns regular JSON format
        - 'csv': Returns CSV format for spreadsheet use

    date_format : str, optional (default='')
        Date format option: '', 'us', 'cn', 'kr', or 'world'
        - '': Unix timestamp (default for JSON)
        - 'us': MM/DD/YYYY
        - 'cn' or 'kr': YYYY/MM/DD
        - 'world': DD/MM/YYYY (default for CSV)

    Returns:
    --------
    Union[Dict, str]
        If format_type='json': Returns dictionary with index data
        If format_type='csv': Returns CSV formatted string

    Example:
    --------
    >>> # Get latest value
    >>> data = get_fear_greed_index()
    >>> print(data['data'][0]['value'])
    >>> print(data['data'][0]['value_classification'])

    >>> # Get last 30 days
    >>> data = get_fear_greed_index(limit=30)

    >>> # Get all data
    >>> data = get_fear_greed_index(limit=0)

    >>> # Get CSV format
    >>> csv_data = get_fear_greed_index(limit=10, format_type='csv')
    """

    # Base URL
    base_url = "https://api.alternative.me/fng/"

    # Build parameters
    params = {}

    if limit != 1:  # Only add if not default
        params['limit'] = limit

    if format_type != 'json':  # Only add if not default
        params['format'] = format_type

    if date_format:  # Only add if specified
        params['date_format'] = date_format

    try:
        # Make API request
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes

        # Return based on format
        if format_type == 'csv':
            return response.text
        else:
            return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Fear and Greed Index: {e}")
        return None


def get_latest_fear_greed() -> Optional[Dict]:
    """
    Convenience function to get just the latest Fear and Greed Index value.

    Returns:
    --------
    Optional[Dict]
        Dictionary with 'value', 'value_classification', 'timestamp',
        and 'time_until_update' keys, or None if error occurs

    Example:
    --------
    >>> latest = get_latest_fear_greed()
    >>> print(f"Current index: {latest['value']} - {latest['value_classification']}")
    """
    data = get_fear_greed_index(limit=1)

    if data and 'data' in data and len(data['data']) > 0:
        return data['data'][0]
    return None


def fear_greed_to_dataframe(limit: int = 30) -> Optional[pd.DataFrame]:
    """
    Get Fear and Greed Index data as a pandas DataFrame.

    Parameters:
    -----------
    limit : int, optional (default=30)
        Number of historical records to retrieve

    Returns:
    --------
    Optional[pd.DataFrame]
        DataFrame with columns: timestamp, value, value_classification
        Index is set to datetime

    Example:
    --------
    >>> df = fear_greed_to_dataframe(limit=30)
    >>> print(df.head())
    >>> df.plot(y='value', title='Fear and Greed Index - Last 30 Days')
    """
    data = get_fear_greed_index(limit=limit)

    if not data or 'data' not in data:
        return None

    # Convert to DataFrame
    df = pd.DataFrame(data['data'])

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')

    # Set timestamp as index
    df.set_index('timestamp', inplace=True)

    # Convert value to numeric
    df['value'] = pd.to_numeric(df['value'])

    # Sort by date (oldest to newest)
    df.sort_index(inplace=True)

    return df


# Example usage
if __name__ == "__main__":
    print("=== Latest Fear and Greed Index ===")
    latest = get_latest_fear_greed()
    if latest:
        print(f"Value: {latest['value']}")
        print(f"Classification: {latest['value_classification']}")
        print(f"Timestamp: {latest['timestamp']}")
        print(f"Time until update: {latest.get('time_until_update', 'N/A')} seconds")

    print("\n=== Last 10 Days ===")
    data = get_fear_greed_index(limit=10, date_format='us')
    if data and 'data' in data:
        for entry in data['data']:
            print(f"{entry['timestamp']}: {entry['value']} - {entry['value_classification']}")

    print("\n=== DataFrame Example ===")
    df = fear_greed_to_dataframe(limit=30)
    if df is not None:
        print(df.head())
        print(f"\nDataFrame shape: {df.shape}")
        print(f"Average value (last 30 days): {df['value'].mean():.2f}")
