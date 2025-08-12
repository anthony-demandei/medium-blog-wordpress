#!/usr/bin/env python3
"""Test Medium API search with corrected field"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.medium_api import MediumAPI
from src.config import Config

def test_search():
    """Test Medium API search functionality"""
    
    print("Testing Medium API Search...")
    print(f"API Key: {Config.RAPIDAPI_KEY[:10]}..." if Config.RAPIDAPI_KEY else "NO API KEY!")
    print("-" * 50)
    
    # Initialize API
    api = MediumAPI(Config.RAPIDAPI_KEY, Config.RAPIDAPI_HOST)
    
    # Test search
    query = "python"
    print(f"\nSearching for: '{query}'")
    print("-" * 50)
    
    articles = api.search_articles(query, limit=3)
    
    if articles:
        print(f"\n✅ Found {len(articles)} articles:")
        for i, article in enumerate(articles, 1):
            print(f"\n{i}. {article.get('title', 'No title')}")
            print(f"   Author: {article.get('author', 'Unknown')}")
            print(f"   URL: {article.get('url', 'No URL')}")
            print(f"   Claps: {article.get('claps', 0)}")
            print(f"   Content length: {len(article.get('content', ''))} chars")
        return True
    else:
        print("\n❌ No articles found")
        return False

if __name__ == "__main__":
    success = test_search()
    sys.exit(0 if success else 1)