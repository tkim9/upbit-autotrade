#!/usr/bin/env python3
"""
Test script for the updated news.py module using SerpAPI
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import functions
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions.news import get_google_news, get_crypto_news, news_to_dataframe

load_dotenv()

def test_serpapi_integration():
    """Test the SerpAPI integration with a simple query"""

    # Get API key from environment
    api_key = os.getenv("SERP_API_KEY")

    if not api_key:
        print("❌ SERP_API_KEY not found in environment variables")
        print("Please set your SerpAPI key in .env file or environment")
        return False

    print("✅ API key found")

    # Test basic news search
    print("\n🔍 Testing basic news search...")
    try:
        news = get_google_news(
            api_key=api_key,
            query="Bitcoin cryptocurrency",
            time_period="qdr:d",  # Past day
            num=5
        )

        if news and 'news_results' in news:
            print(f"✅ Found {len(news['news_results'])} news articles")

            # Test DataFrame conversion
            print("\n📊 Testing DataFrame conversion...")
            df = news_to_dataframe(news)
            if df is not None and not df.empty:
                print(f"✅ DataFrame created with {len(df)} rows")
                print("Sample data:")
                print(df[['title', 'source']].head(2))
            else:
                print("❌ DataFrame conversion failed")
                return False
        else:
            print("❌ No news results found")
            return False

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

    # Test crypto news function
    print("\n💰 Testing crypto news function...")
    try:
        crypto_news = get_crypto_news(
            api_key=api_key,
            crypto_name="Ethereum",
            time_period="qdr:w",  # Past week
            num=3
        )

        if crypto_news and 'news_results' in crypto_news:
            print(f"✅ Found {len(crypto_news['news_results'])} crypto news articles")
        else:
            print("❌ No crypto news results found")
            return False

    except Exception as e:
        print(f"❌ Error during crypto news testing: {e}")
        return False

    print("\n🎉 All tests passed! SerpAPI integration is working correctly.")
    return True

if __name__ == "__main__":
    test_serpapi_integration()


