#!/usr/bin/env python3
"""Test new Medium API endpoints"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.medium_api import MediumAPI
from src.config import Config

def test_trending():
    """Test trending articles endpoint"""
    print("=" * 60)
    print("TESTING TRENDING ARTICLES")
    print("=" * 60)
    
    api = MediumAPI(Config.RAPIDAPI_KEY, Config.RAPIDAPI_HOST)
    
    # Test hot articles
    print("\n📍 Testing HOT articles for 'programming'...")
    articles = api.get_trending_articles(tag='programming', mode='hot', limit=3)
    
    if articles:
        print(f"✅ Found {len(articles)} hot articles:")
        for i, article in enumerate(articles, 1):
            print(f"\n{i}. {article.get('title', 'No title')}")
            print(f"   Claps: {article.get('claps', 0)}")
            print(f"   Format: {article.get('content_format', 'unknown')}")
            print(f"   Trending: {article.get('trending_type')} in {article.get('trending_tag')}")
    else:
        print("❌ No hot articles found")
    
    return len(articles) > 0

def test_latest_posts():
    """Test latest posts by topic"""
    print("\n" + "=" * 60)
    print("TESTING LATEST POSTS BY TOPIC")
    print("=" * 60)
    
    api = MediumAPI(Config.RAPIDAPI_KEY, Config.RAPIDAPI_HOST)
    
    print("\n📍 Testing latest posts for 'artificial-intelligence'...")
    articles = api.get_latest_posts(topic='artificial-intelligence', limit=3)
    
    if articles:
        print(f"✅ Found {len(articles)} latest posts:")
        for i, article in enumerate(articles, 1):
            print(f"\n{i}. {article.get('title', 'No title')}")
            print(f"   Topic: {article.get('topic')}")
            print(f"   Author: {article.get('author', 'Unknown')}")
    else:
        print("❌ No latest posts found")
    
    return len(articles) > 0

def test_related_articles():
    """Test related articles"""
    print("\n" + "=" * 60)
    print("TESTING RELATED ARTICLES")
    print("=" * 60)
    
    api = MediumAPI(Config.RAPIDAPI_KEY, Config.RAPIDAPI_HOST)
    
    # Use a known article ID
    article_id = "6887501cf5ee"
    print(f"\n📍 Testing related articles for ID: {article_id}...")
    
    related = api.get_related_articles(article_id)
    
    if related:
        print(f"✅ Found {len(related)} related articles:")
        for i, article in enumerate(related, 1):
            print(f"\n{i}. {article.get('title', 'No title')}")
            print(f"   ID: {article.get('id')}")
    else:
        print("❌ No related articles found")
    
    return len(related) > 0

def test_user_info():
    """Test user info endpoint"""
    print("\n" + "=" * 60)
    print("TESTING USER INFO")
    print("=" * 60)
    
    api = MediumAPI(Config.RAPIDAPI_KEY, Config.RAPIDAPI_HOST)
    
    # Use a known user ID
    user_id = "92af3948e758"
    print(f"\n📍 Testing user info for ID: {user_id}...")
    
    user = api.get_user_info(user_id)
    
    if user:
        print(f"✅ User found:")
        print(f"   Name: {user.get('fullname')}")
        print(f"   Username: {user.get('username')}")
        print(f"   Followers: {user.get('followers_count')}")
        print(f"   Bio: {user.get('bio', '')[:100]}...")
        print(f"   Top Writer In: {', '.join(user.get('top_writer_in', []))}")
    else:
        print("❌ User not found")
    
    return user is not None

def test_markdown_content():
    """Test markdown content endpoint"""
    print("\n" + "=" * 60)
    print("TESTING MARKDOWN CONTENT")
    print("=" * 60)
    
    api = MediumAPI(Config.RAPIDAPI_KEY, Config.RAPIDAPI_HOST)
    
    article_id = "6887501cf5ee"
    print(f"\n📍 Testing markdown content for ID: {article_id}...")
    
    content = api.get_article_content(article_id, format='markdown')
    
    if content:
        print(f"✅ Markdown content retrieved:")
        print(f"   Length: {len(content)} characters")
        print(f"   Preview: {content[:200]}...")
    else:
        print("❌ No markdown content found")
    
    return content is not None

if __name__ == "__main__":
    print("\n🚀 TESTING NEW MEDIUM API ENDPOINTS\n")
    
    results = {
        "Trending": test_trending(),
        "Latest Posts": test_latest_posts(),
        "Related Articles": test_related_articles(),
        "User Info": test_user_info(),
        "Markdown Content": test_markdown_content()
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("✅ ALL TESTS PASSED!" if all_passed else "❌ SOME TESTS FAILED"))
    
    sys.exit(0 if all_passed else 1)