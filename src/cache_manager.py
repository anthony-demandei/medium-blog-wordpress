import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from database import Database
from medium_api import MediumAPI
from translator import GeminiTranslator

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, db: Database, medium_api: MediumAPI, translator: GeminiTranslator):
        self.db = db
        self.medium_api = medium_api
        self.translator = translator
    
    def cache_article(self, article: Dict) -> bool:
        """Cache a single article"""
        try:
            # Check if already cached
            existing = self.db.get_cache(article.get('id'))
            if existing:
                return True
            
            # Cache the article
            self.db.cache_article(
                medium_id=article.get('id'),
                original_title=article.get('title'),
                original_subtitle=article.get('subtitle'),
                original_content=article.get('content'),
                author=article.get('author'),
                author_id=article.get('author_id'),
                url=article.get('url'),
                cover_image=article.get('image_url'),
                tags=article.get('tags', []),
                claps=article.get('claps', 0),
                reading_time=article.get('reading_time', 0)
            )
            return True
        except Exception as e:
            logger.error(f"Error caching article: {e}")
            return False
    
    def get_or_fetch_article(self, medium_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """Get article from cache or fetch from Medium"""
        
        # Check cache first unless force refresh
        if not force_refresh:
            cached = self.db.get_cache(medium_id)
            if cached:
                logger.info(f"Article {medium_id} found in cache")
                return cached
        
        # Fetch from Medium API
        logger.info(f"Fetching article {medium_id} from Medium")
        article = self.medium_api.get_article_info(medium_id)
        
        if not article:
            logger.error(f"Failed to fetch article {medium_id}")
            return None
        
        # Save to cache
        self.db.save_cache(article)
        
        # Get the saved cache (includes extracted images)
        return self.db.get_cache(medium_id)
    
    def translate_cached_article(self, medium_id: str, target_lang: str = 'pt') -> Optional[Dict]:
        """Translate a cached article"""
        
        # Get from cache
        cached = self.db.get_cache(medium_id)
        if not cached:
            # Try to fetch if not in cache
            cached = self.get_or_fetch_article(medium_id)
            if not cached:
                return None
        
        # Check if already translated
        if cached.get('is_translated'):
            logger.info(f"Article {medium_id} already translated")
            return cached
        
        # Translate using Gemini
        if not self.translator.enabled:
            logger.warning("Translator not enabled")
            return cached
        
        logger.info(f"Translating article {medium_id}")
        
        # Prepare article data for translation
        article_data = {
            'title': cached['original_title'],
            'subtitle': cached['original_subtitle'],
            'content': cached['original_content'],
            'lang': 'en'  # Assume English source
        }
        
        # Translate
        translated = self.translator.translate_article(article_data, target_lang)
        
        # Update cache with translation
        translated_data = {
            'title': translated.get('title'),
            'subtitle': translated.get('subtitle'),
            'content': translated.get('content')
        }
        
        # Save translation to cache
        self.db.save_cache(
            {'id': medium_id},  # Minimal data needed for cache update
            translated_data
        )
        
        # Return updated cache
        return self.db.get_cache(medium_id)
    
    def search_and_cache(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for articles and cache them"""
        
        logger.info(f"Searching for '{query}' with limit {limit}")
        
        # Search using Medium API
        articles = self.medium_api.search_articles(query, limit)
        
        cached_articles = []
        for article in articles:
            # Check if already cached
            cached = self.db.get_cache(article['id'])
            if cached:
                cached_articles.append(cached)
            else:
                # Save to cache
                self.db.save_cache(article)
                cached = self.db.get_cache(article['id'])
                if cached:
                    cached_articles.append(cached)
        
        return cached_articles
    
    def get_comparison_data(self, medium_id: str) -> Optional[Dict]:
        """Get both original and translated versions for comparison"""
        
        # Get cached article
        cached = self.db.get_cache(medium_id)
        if not cached:
            cached = self.get_or_fetch_article(medium_id)
            if not cached:
                return None
        
        # Translate if not already translated
        if not cached.get('is_translated'):
            cached = self.translate_cached_article(medium_id)
        
        # Prepare comparison data
        comparison_data = {
            'medium_id': medium_id,
            'original': {
                'title': cached.get('original_title'),
                'subtitle': cached.get('original_subtitle'),
                'content': cached.get('original_content'),
                'author': cached.get('author'),
                'cover_image': cached.get('cover_image'),
                'images': cached.get('images', [])
            },
            'translated': {
                'title': cached.get('translated_title'),
                'subtitle': cached.get('translated_subtitle'),
                'content': cached.get('translated_content')
            },
            'metadata': {
                'url': cached.get('url'),
                'claps': cached.get('claps'),
                'reading_time': cached.get('reading_time'),
                'tags': cached.get('tags', []),
                'cached_at': cached.get('cached_at'),
                'expires_at': cached.get('expires_at')
            }
        }
        
        return comparison_data
    
    def clear_cache(self) -> int:
        """Clear expired cache entries"""
        count = self.db.clear_expired_cache()
        logger.info(f"Cleared {count} expired cache entries")
        return count
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        all_cached = self.db.get_all_cached_articles()
        
        translated_count = sum(1 for article in all_cached if article.get('is_translated'))
        
        return {
            'total_cached': len(all_cached),
            'translated': translated_count,
            'not_translated': len(all_cached) - translated_count,
            'cache_size_mb': 0  # Could calculate actual size if needed
        }