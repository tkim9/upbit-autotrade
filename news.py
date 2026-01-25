import requests
from typing import Optional, Dict, List
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SERP_API_KEY")


def get_google_news(
    query: str,
    api_key: str = API_KEY,
    location: Optional[str] = None,
    gl: str = "us",
    hl: str = "en",
    time_period: Optional[str] = None,
    time_period_min: Optional[str] = None,
    time_period_max: Optional[str] = None,
    sort_by: Optional[str] = None,
    num: int = 10,
    page: int = 1,
    safe: str = "off",
    device: str = "desktop"
) -> Optional[Dict]:
    """
    Fetch news articles from Google News using SerpAPI.

    Source: https://serpapi.com/google-news-api

    Parameters:
    -----------
    api_key : str
        Your SerpAPI API key (required)

    query : str
        Search terms (required). Examples:
        - "climate change"
        - "Bitcoin news"
        - "site:nytimes.com technology"

    location : str, optional
        Geographic location for search (e.g., "New York,United States")

    gl : str, optional (default="us")
        Country code for search (e.g., "us", "uk", "kr")

    hl : str, optional (default="en")
        Interface language (e.g., "en", "ko", "ja")

    time_period : str, optional
        Time filter for results (SerpAPI tbs format):
        - "qdr:h": Past hour
        - "qdr:d": Past 24 hours
        - "qdr:w": Past week
        - "qdr:m": Past month
        - "qdr:y": Past year

    time_period_min : str, optional
        Start date for custom period (format: MM/DD/YYYY)

    time_period_max : str, optional
        End date for custom period (format: MM/DD/YYYY)

    sort_by : str, optional
        Sort results: "relevance" (default) or "date"

    num : int, optional (default=10)
        Number of results per page

    page : int, optional (default=1)
        Page number for pagination

    safe : str, optional (default="off")
        SafeSearch filter: "active" or "off"

    device : str, optional (default="desktop")
        Device type: "desktop", "mobile", or "tablet"

    Returns:
    --------
    Optional[Dict]
        Dictionary containing news results with keys:
        - search_metadata: Request metadata
        - search_parameters: Search parameters used
        - search_information: Search statistics
        - news_results: List of news articles
        - top_stories: Featured stories (if available)
        - pagination: Pagination information

    Example:
    --------
    >>> news = get_google_news(
    ...     api_key="your_api_key",
    ...     query="Cardano ADA cryptocurrency",
    ...     time_period="last_week",
    ...     sort_by="most_recent",
    ...     num=20
    ... )
    >>> for article in news['news_results']:
    ...     print(f"{article['title']} - {article['source']}")
    """

    base_url = "https://serpapi.com/search.json"

    # Build parameters
    params = {
        "engine": "google_news",
        "api_key": api_key,
        "q": query,
        "gl": gl,
        "hl": hl,
        "num": num,
        "start": (page - 1) * num,  # SerpAPI uses 'start' instead of 'page'
        "safe": safe,
        "device": device
    }

    # Add optional parameters
    if location:
        params["location"] = location

    if time_period:
        params["tbs"] = time_period  # SerpAPI uses 'tbs' for time period

    if time_period_min:
        params["tbs"] = f"cdr:1,cd_min:{time_period_min}"

    if time_period_max:
        if "tbs" in params:
            params["tbs"] += f",cd_max:{time_period_max}"
        else:
            params["tbs"] = f"cdr:1,cd_max:{time_period_max}"

    if sort_by:
        params["sort"] = sort_by  # SerpAPI uses 'sort' instead of 'sort_by'

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Google News: {e}")
        return None


def get_crypto_news(
    crypto_name: str,
    api_key: str = API_KEY,
    time_period: str = "qdr:w",
    num: int = 20
) -> Optional[Dict]:
    """
    Convenience function to get cryptocurrency news.

    Parameters:
    -----------
    api_key : str
        Your SerpAPI API key

    crypto_name : str
        Cryptocurrency name (e.g., "Bitcoin", "Cardano", "ADA")

    time_period : str, optional (default="qdr:w")
        Time period for news (SerpAPI format)

    num : int, optional (default=20)
        Number of results to fetch

    Returns:
    --------
    Optional[Dict]
        News results dictionary

    Example:
    --------
    >>> news = get_crypto_news(api_key="your_key", crypto_name="Cardano ADA")
    """
    query = f"{crypto_name} cryptocurrency news"
    return get_google_news(
        api_key=api_key,
        query=query,
        time_period=time_period,
        sort_by="date",
        num=num
    )


def news_to_dataframe(news_data: Dict, verbose: bool = False) -> Optional[pd.DataFrame]:
    """
    Convert Google News API response to a pandas DataFrame.

    Parameters:
    -----------
    news_data : Dict
        Response from get_google_news()

    verbose : bool, optional (default=False)
        Whether to print verbose output

    Returns:
    --------
    Optional[pd.DataFrame]
        DataFrame with columns: title, link, source, date, snippet

    Example:
    --------
    >>> news = get_google_news(api_key="key", query="Bitcoin")
    >>> df = news_to_dataframe(news)
    >>> print(df[['title', 'source', 'date']])
    """
    if not news_data or 'news_results' not in news_data:
        return None

    articles = []
    if verbose:
        for article in news_data['news_results']:
            articles.append({
                'title': article.get('title', ''),
                'link': article.get('link', ''),
                'source': article.get('source', ''),
                'date': article.get('date', ''),
                'snippet': article.get('snippet', ''),
                'position': article.get('position', 0)
            })
    else:
        for article in news_data['news_results']:
            articles.append({
                'title': article.get('title', ''),
                'date': article.get('date', ''),
            })
    df = pd.DataFrame(articles)
    return df


def extract_article_summaries(news_data: Dict, max_articles: int = 10) -> List[Dict]:
    """
    Extract clean summaries from news results for AI analysis.

    Parameters:
    -----------
    news_data : Dict
        Response from get_google_news()

    max_articles : int, optional (default=10)
        Maximum number of articles to extract

    Returns:
    --------
    List[Dict]
        List of dictionaries with title, source, date, and snippet

    Example:
    --------
    >>> news = get_google_news(api_key="key", query="ADA price")
    >>> summaries = extract_article_summaries(news, max_articles=5)
    >>> for article in summaries:
    ...     print(f"{article['source']}: {article['title']}")
    """
    if not news_data or 'news_results' not in news_data:
        return []

    summaries = []
    for article in news_data['news_results'][:max_articles]:
        summaries.append({
            'title': article.get('title', ''),
            'source': article.get('source', ''),
            'date': article.get('date', ''),
            'snippet': article.get('snippet', '')
        })

    return summaries


def get_news_sentiment_summary(
    query: str,
    api_key: str = API_KEY,
    time_period: str = "qdr:w",
    num: int = 20
) -> str:
    """
    Get news articles and format them as a text summary for AI analysis.

    Parameters:
    -----------
    api_key : str
        Your SerpAPI API key

    query : str
        Search query

    time_period : str, optional (default="qdr:w")
        Time period for news (SerpAPI format)

    num : int, optional (default=20)
        Number of articles to fetch

    Returns:
    --------
    str
        Formatted text summary of recent news articles

    Example:
    --------
    >>> summary = get_news_sentiment_summary(
    ...     api_key="key",
    ...     query="Cardano ADA",
    ...     time_period="last_day"
    ... )
    >>> print(summary)
    """
    news = get_google_news(
        api_key=api_key,
        query=query,
        time_period=time_period,
        sort_by="date",
        num=num
    )

    if not news or 'news_results' not in news:
        return "No recent news found."

    summaries = extract_article_summaries(news, max_articles=num)

    # Format as text
    text_summary = f"Recent news for '{query}' ({time_period}):\n\n"

    for i, article in enumerate(summaries, 1):
        text_summary += f"{i}. {article['title']}\n"
        text_summary += f"   Date: {article['date']}\n\n"

    return text_summary


# Example usage
if __name__ == "__main__":
    print("=== Example 1: Get Cardano ADA News ===")
    news = get_crypto_news(
        api_key=API_KEY,
        crypto_name="Cardano ADA",
        time_period="qdr:w",  # Past week in SerpAPI format
        num=5
    )
    print(news)

    if news and 'news_results' in news:
        for article in news['news_results']:
            print(f"\n{article['title']}")
            print(f"Date: {article['date']}")

    print("\n=== Example 2: Convert to DataFrame ===")
    df = news_to_dataframe(news)
    if df is not None:
        print(df[['title', 'date']])

    print("\n=== Example 3: Get News Summary for AI ===")
    summary = get_news_sentiment_summary(
        api_key=API_KEY,
        query="Bitcoin price prediction",
        time_period="qdr:d",  # Past day in SerpAPI format
        num=5
    )
    print(summary)