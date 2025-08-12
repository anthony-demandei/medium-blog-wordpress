#!/usr/bin/env python3
"""Test Medium API connection and search"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config

def test_direct_api():
    """Test direct API call to Medium"""
    
    print("Testing Direct Medium API Connection...")
    print(f"API Key: {Config.RAPIDAPI_KEY[:10]}..." if Config.RAPIDAPI_KEY else "NO API KEY!")
    print(f"API Host: {Config.RAPIDAPI_HOST}")
    print("-" * 50)
    
    if not Config.RAPIDAPI_KEY:
        print("ERROR: No RapidAPI key configured!")
        return False
    
    # Test direct API call
    url = f"https://{Config.RAPIDAPI_HOST}/search/articles"
    headers = {
        "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
        "X-RapidAPI-Host": Config.RAPIDAPI_HOST
    }
    params = {"query": "python"}
    
    print(f"\nURL: {url}")
    print(f"Headers: X-RapidAPI-Key: {Config.RAPIDAPI_KEY[:10]}...")
    print(f"Headers: X-RapidAPI-Host: {Config.RAPIDAPI_HOST}")
    print(f"Params: {params}")
    print("\nMaking request...")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Success! Response:")
            print(json.dumps(data, indent=2)[:1000])  # First 1000 chars
            
            article_ids = data.get('article_ids', [])
            if article_ids:
                print(f"\nFound {len(article_ids)} article IDs")
                print(f"First 5 IDs: {article_ids[:5]}")
                
                # Test getting first article
                if article_ids:
                    print(f"\n\nTesting article fetch for ID: {article_ids[0]}")
                    article_url = f"https://{Config.RAPIDAPI_HOST}/article/{article_ids[0]}"
                    article_response = requests.get(article_url, headers=headers, timeout=10)
                    print(f"Article Status Code: {article_response.status_code}")
                    if article_response.status_code == 200:
                        article_data = article_response.json()
                        print(f"Article Title: {article_data.get('title', 'No title')}")
                        print(f"Article Author: {article_data.get('author', 'Unknown')}")
            else:
                print("\n⚠️ No article IDs in response")
        else:
            print(f"\n❌ Error Response:")
            print(f"Text: {response.text[:500]}")
            
        return response.status_code == 200
        
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_api()
    sys.exit(0 if success else 1)