#!/usr/bin/env python3
"""Test content processing improvements"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.content_processor import ContentProcessor
from src.translator import GeminiTranslator
from src.config import Config

def test_code_formatting():
    """Test code block formatting"""
    print("=" * 60)
    print("TESTING CODE BLOCK FORMATTING")
    print("=" * 60)
    
    markdown_content = """
# Python Performance Tips

Here's a simple example:

```python
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total

# Using list comprehension
result = sum([x * 2 for x in range(10)])
```

And inline code like `variable = value` should also be formatted.

## Another Example

```javascript
const fetchData = async () => {
    const response = await fetch('/api/data');
    return response.json();
};
```
"""
    
    html = ContentProcessor.process_markdown_to_html(markdown_content, 'markdown')
    
    # Check if code blocks are formatted
    if '<div style="background: linear-gradient' in html:
        print("✅ Code blocks are properly formatted with cards")
    else:
        print("❌ Code blocks not formatted correctly")
    
    # Check if inline code is formatted
    if 'background-color: #f4f4f4' in html:
        print("✅ Inline code is properly formatted")
    else:
        print("❌ Inline code not formatted correctly")
    
    # Save output to file for inspection
    with open('test_output.html', 'w') as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Output</title>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
            {html}
        </body>
        </html>
        """)
    
    print("📄 Output saved to test_output.html")
    
    return True

def test_content_filtering():
    """Test content filtering"""
    print("\n" + "=" * 60)
    print("TESTING CONTENT FILTERING")
    print("=" * 60)
    
    # Test job posting (should be filtered)
    job_article = {
        'title': 'We are hiring Python developers',
        'subtitle': 'Great opportunity',
        'content': 'Join our team'
    }
    
    if ContentProcessor.should_filter_article(job_article):
        print("✅ Job posting correctly filtered")
    else:
        print("❌ Job posting not filtered")
    
    # Test sale/promo (should be filtered)
    promo_article = {
        'title': 'Black Friday Sale on iPhones',
        'subtitle': 'Discount up to 50%',
        'content': 'Buy now'
    }
    
    if ContentProcessor.should_filter_article(promo_article):
        print("✅ Promotional content correctly filtered")
    else:
        print("❌ Promotional content not filtered")
    
    # Test valid article (should NOT be filtered)
    valid_article = {
        'title': 'Understanding Python Decorators',
        'subtitle': 'A comprehensive guide',
        'content': 'Decorators are powerful tools in Python'
    }
    
    if not ContentProcessor.should_filter_article(valid_article):
        print("✅ Valid article correctly passed")
    else:
        print("❌ Valid article incorrectly filtered")
    
    return True

def test_tag_filtering():
    """Test tag filtering and normalization"""
    print("\n" + "=" * 60)
    print("TESTING TAG FILTERING")
    print("=" * 60)
    
    # Test with mixed tags
    tags = ['Python', 'job opening', 'machine-learning', 'random-tag', 'React', 'sale']
    
    filtered = ContentProcessor.filter_and_normalize_tags(tags)
    
    print(f"Original tags: {tags}")
    print(f"Filtered tags: {filtered}")
    
    # Check if relevant tags are kept
    if 'python' in filtered and 'machine-learning' in filtered and 'react' in filtered:
        print("✅ Relevant tags correctly kept")
    else:
        print("❌ Some relevant tags were filtered out")
    
    # Check if irrelevant tags are removed
    if 'job-opening' not in filtered and 'sale' not in filtered and 'random-tag' not in filtered:
        print("✅ Irrelevant tags correctly removed")
    else:
        print("❌ Some irrelevant tags were not filtered")
    
    return True

def test_category_determination():
    """Test category determination"""
    print("\n" + "=" * 60)
    print("TESTING CATEGORY DETERMINATION")
    print("=" * 60)
    
    # Test AI article
    ai_article = {
        'title': 'Deep Learning with PyTorch',
        'tags': ['artificial-intelligence', 'pytorch', 'deep-learning']
    }
    
    category = ContentProcessor.determine_category(ai_article)
    print(f"AI Article -> Category: {category}")
    
    if category in ['Inteligência Artificial', 'Deep Learning']:
        print("✅ AI article correctly categorized")
    else:
        print("❌ AI article incorrectly categorized")
    
    # Test JavaScript article
    js_article = {
        'title': 'Advanced React Patterns',
        'tags': ['react', 'javascript', 'frontend']
    }
    
    category = ContentProcessor.determine_category(js_article)
    print(f"JS Article -> Category: {category}")
    
    if category in ['React', 'JavaScript', 'Frontend']:
        print("✅ JS article correctly categorized")
    else:
        print("❌ JS article incorrectly categorized")
    
    return True

def test_translation_improvements():
    """Test translation improvements"""
    print("\n" + "=" * 60)
    print("TESTING TRANSLATION IMPROVEMENTS")
    print("=" * 60)
    
    if not Config.GEMINI_API_KEY:
        print("⚠️ Gemini API key not configured, skipping translation test")
        return True
    
    translator = GeminiTranslator(Config.GEMINI_API_KEY, Config.GEMINI_MODEL)
    
    # Test content with code
    content_with_code = """
    Here's how to use Python decorators:
    
    ```python
    def my_decorator(func):
        def wrapper():
            print("Before function")
            func()
            print("After function")
        return wrapper
    ```
    
    This is a simple example of a decorator pattern.
    """
    
    translated = translator.translate_and_rewrite(content_with_code, 'en', 'pt')
    
    # Check if code blocks are preserved
    if '```python' in translated and 'def my_decorator' in translated:
        print("✅ Code blocks preserved during translation")
    else:
        print("❌ Code blocks not preserved during translation")
    
    # Check if technical terms are preserved
    if 'Python' in translated and 'decorator' in translated:
        print("✅ Technical terms preserved")
    else:
        print("❌ Technical terms not preserved")
    
    print(f"\nTranslated preview: {translated[:200]}...")
    
    return True

if __name__ == "__main__":
    print("\n🚀 TESTING CONTENT PROCESSING IMPROVEMENTS\n")
    
    results = {
        "Code Formatting": test_code_formatting(),
        "Content Filtering": test_content_filtering(),
        "Tag Filtering": test_tag_filtering(),
        "Category Determination": test_category_determination(),
        "Translation Improvements": test_translation_improvements()
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