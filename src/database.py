from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import os
import json
import re

logger = logging.getLogger(__name__)

Base = declarative_base()

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    medium_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    author = Column(String(255))
    url = Column(Text)
    wordpress_post_id = Column(Integer)
    wordpress_post_url = Column(Text)
    published_at = Column(DateTime)
    synced_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='synced')
    
    def to_dict(self):
        return {
            'id': self.id,
            'medium_id': self.medium_id,
            'title': self.title,
            'author': self.author,
            'url': self.url,
            'wordpress_post_id': self.wordpress_post_id,
            'wordpress_post_url': self.wordpress_post_url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'status': self.status
        }

class SyncLog(Base):
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True)
    sync_date = Column(DateTime, default=datetime.utcnow)
    articles_found = Column(Integer, default=0)
    articles_synced = Column(Integer, default=0)
    articles_skipped = Column(Integer, default=0)
    errors = Column(Text)
    status = Column(String(50), default='success')
    
    def to_dict(self):
        return {
            'id': self.id,
            'sync_date': self.sync_date.isoformat() if self.sync_date else None,
            'articles_found': self.articles_found,
            'articles_synced': self.articles_synced,
            'articles_skipped': self.articles_skipped,
            'errors': self.errors,
            'status': self.status
        }

class TrendingCache(Base):
    __tablename__ = 'trending_cache'
    
    id = Column(Integer, primary_key=True)
    cache_key = Column(String(255), unique=True, nullable=False)  # e.g., "trending_programming_hot"
    articles_data = Column(JSON)  # Serialized articles list
    cached_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            # Trending cache expires after 24 hours
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

class ArticleCache(Base):
    __tablename__ = 'article_cache'
    
    id = Column(Integer, primary_key=True)
    medium_id = Column(String(255), unique=True, nullable=False)
    original_content = Column(Text)
    translated_content = Column(Text)
    original_title = Column(String(500))
    translated_title = Column(String(500))
    original_subtitle = Column(Text)
    translated_subtitle = Column(Text)
    author = Column(String(255))
    cover_image = Column(Text)
    images = Column(JSON)  # List of image URLs in the article
    tags = Column(JSON)
    claps = Column(Integer)
    reading_time = Column(Integer)
    url = Column(Text)
    cached_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_translated = Column(Boolean, default=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=7)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self):
        return {
            'id': self.id,
            'medium_id': self.medium_id,
            'original_content': self.original_content,
            'translated_content': self.translated_content,
            'original_title': self.original_title,
            'translated_title': self.translated_title,
            'original_subtitle': self.original_subtitle,
            'translated_subtitle': self.translated_subtitle,
            'author': self.author,
            'cover_image': self.cover_image,
            'images': self.images,
            'tags': self.tags,
            'claps': self.claps,
            'reading_time': self.reading_time,
            'url': self.url,
            'cached_at': self.cached_at.isoformat() if self.cached_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_translated': self.is_translated,
            'is_expired': self.is_expired()
        }

class AutomationSettings(Base):
    __tablename__ = 'automation_settings'
    
    id = Column(Integer, primary_key=True)
    automation_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'automation_enabled': self.automation_enabled,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ApiUsage(Base):
    __tablename__ = 'api_usage'
    
    id = Column(Integer, primary_key=True)
    month = Column(String(7), nullable=False)  # Format: YYYY-MM
    requests_used = Column(Integer, default=0)
    requests_limit = Column(Integer, default=2500)
    last_reset = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'month': self.month,
            'requests_used': self.requests_used,
            'requests_limit': self.requests_limit,
            'requests_remaining': self.requests_limit - self.requests_used,
            'percentage_used': round((self.requests_used / self.requests_limit) * 100, 1),
            'last_reset': self.last_reset.isoformat() if self.last_reset else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Database:
    def __init__(self, database_path: str):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        
        self.engine = create_engine(f'sqlite:///{database_path}')
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    def article_exists(self, medium_id: str) -> bool:
        """Check if article already exists in database"""
        with self.get_session() as session:
            return session.query(Article).filter_by(medium_id=medium_id).first() is not None
    
    def save_article(self, article_data: dict, wordpress_data: dict = None) -> Article:
        """Save article to database"""
        with self.get_session() as session:
            # Check if article already exists
            existing = session.query(Article).filter_by(medium_id=article_data['id']).first()
            
            if existing:
                # Update existing article
                if wordpress_data:
                    existing.wordpress_post_id = wordpress_data.get('id')
                    existing.wordpress_post_url = wordpress_data.get('link')
                    existing.status = 'synced'
                session.commit()
                return existing
            
            # Create new article
            article = Article(
                medium_id=article_data['id'],
                title=article_data.get('title', ''),
                author=article_data.get('author', ''),
                url=article_data.get('url', ''),
                published_at=self._parse_date(article_data.get('published_at'))
            )
            
            if wordpress_data:
                article.wordpress_post_id = wordpress_data.get('id')
                article.wordpress_post_url = wordpress_data.get('link')
                article.status = 'synced'
            
            session.add(article)
            session.commit()
            return article
    
    def create_sync_log(self, found: int, synced: int, skipped: int, errors: str = None) -> SyncLog:
        """Create a sync log entry"""
        with self.get_session() as session:
            log = SyncLog(
                articles_found=found,
                articles_synced=synced,
                articles_skipped=skipped,
                errors=errors,
                status='error' if errors else 'success'
            )
            session.add(log)
            session.commit()
            return log
    
    def get_recent_articles(self, limit: int = 10) -> list:
        """Get recent synced articles"""
        with self.get_session() as session:
            articles = session.query(Article)\
                .order_by(Article.synced_at.desc())\
                .limit(limit)\
                .all()
            return [article.to_dict() for article in articles]
    
    def get_sync_logs(self, limit: int = 10) -> list:
        """Get recent sync logs"""
        with self.get_session() as session:
            logs = session.query(SyncLog)\
                .order_by(SyncLog.sync_date.desc())\
                .limit(limit)\
                .all()
            return [log.to_dict() for log in logs]
    
    def get_statistics(self) -> dict:
        """Get sync statistics"""
        with self.get_session() as session:
            total_articles = session.query(Article).count()
            total_syncs = session.query(SyncLog).count()
            successful_syncs = session.query(SyncLog).filter_by(status='success').count()
            
            # Get last sync info
            last_sync = session.query(SyncLog)\
                .order_by(SyncLog.sync_date.desc())\
                .first()
            
            return {
                'total_articles': total_articles,
                'total_syncs': total_syncs,
                'successful_syncs': successful_syncs,
                'last_sync': last_sync.to_dict() if last_sync else None
            }
    
    def _parse_date(self, date_string: str):
        """Parse date string to datetime object"""
        if not date_string:
            return None
        
        try:
            # Handle ISO format with Z timezone
            if date_string.endswith('Z'):
                date_string = date_string[:-1] + '+00:00'
            return datetime.fromisoformat(date_string)
        except:
            return None
    
    def save_cache(self, article_data: dict, translated_data: dict = None) -> ArticleCache:
        """Save article to cache"""
        with self.get_session() as session:
            # Check if cache exists
            existing = session.query(ArticleCache).filter_by(medium_id=article_data['id']).first()
            
            if existing and not existing.is_expired():
                # Update existing cache if provided translated data
                if translated_data:
                    existing.translated_content = translated_data.get('content')
                    existing.translated_title = translated_data.get('title')
                    existing.translated_subtitle = translated_data.get('subtitle')
                    existing.is_translated = True
                session.commit()
                return existing
            elif existing and existing.is_expired():
                # Delete expired cache
                session.delete(existing)
            
            # Extract images from content
            images = self._extract_images(article_data.get('content', ''))
            
            # Create new cache
            cache = ArticleCache(
                medium_id=article_data['id'],
                original_content=article_data.get('content', ''),
                original_title=article_data.get('title', ''),
                original_subtitle=article_data.get('subtitle', ''),
                author=article_data.get('author', ''),
                cover_image=article_data.get('image_url', ''),
                images=images,
                tags=article_data.get('tags', []),
                claps=article_data.get('claps', 0),
                reading_time=article_data.get('reading_time', 0),
                url=article_data.get('url', '')
            )
            
            if translated_data:
                cache.translated_content = translated_data.get('content')
                cache.translated_title = translated_data.get('title')
                cache.translated_subtitle = translated_data.get('subtitle')
                cache.is_translated = True
            
            session.add(cache)
            session.commit()
            return cache
    
    def get_cache(self, medium_id: str):
        """Get article from cache"""
        with self.get_session() as session:
            cache = session.query(ArticleCache).filter_by(medium_id=medium_id).first()
            if cache and not cache.is_expired():
                return cache.to_dict()
            elif cache and cache.is_expired():
                session.delete(cache)
                session.commit()
            return None
    
    def get_all_cached_articles(self) -> list:
        """Get all non-expired cached articles"""
        with self.get_session() as session:
            # Delete expired caches first
            expired = session.query(ArticleCache).filter(
                ArticleCache.expires_at < datetime.utcnow()
            ).all()
            for cache in expired:
                session.delete(cache)
            session.commit()
            
            # Get valid caches
            caches = session.query(ArticleCache).filter(
                ArticleCache.expires_at >= datetime.utcnow()
            ).order_by(ArticleCache.cached_at.desc()).all()
            
            return [cache.to_dict() for cache in caches]
    
    def clear_expired_cache(self):
        """Clear all expired cache entries"""
        with self.get_session() as session:
            expired = session.query(ArticleCache).filter(
                ArticleCache.expires_at < datetime.utcnow()
            ).all()
            count = len(expired)
            for cache in expired:
                session.delete(cache)
            session.commit()
            return count
    
    def _extract_images(self, content: str) -> list:
        """Extract image URLs from HTML content"""
        images = []
        if not content:
            return images
        
        # Simple regex to find image URLs
        img_pattern = r'<img[^>]+src=["\']([^"\'>]+)["\']'
        matches = re.findall(img_pattern, content)
        images.extend(matches)
        
        # Also look for Medium-style image URLs
        medium_pattern = r'https://[^\s"<>]+\.(?:png|jpg|jpeg|gif|webp)'
        matches = re.findall(medium_pattern, content)
        images.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        
        return unique_images
    
    def get_automation_settings(self) -> AutomationSettings:
        """Get automation settings"""
        with self.get_session() as session:
            settings = session.query(AutomationSettings).first()
            if not settings:
                settings = AutomationSettings(automation_enabled=True)
                session.add(settings)
                session.commit()
            return settings.to_dict()
    
    def set_automation_enabled(self, enabled: bool) -> bool:
        """Enable or disable automation"""
        with self.get_session() as session:
            settings = session.query(AutomationSettings).first()
            if not settings:
                settings = AutomationSettings()
                session.add(settings)
            settings.automation_enabled = enabled
            settings.updated_at = datetime.utcnow()
            session.commit()
            return True
    
    def get_api_usage(self) -> ApiUsage:
        """Get or create API usage for current month"""
        with self.get_session() as session:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            # Get or create usage record for current month
            usage = session.query(ApiUsage).filter_by(month=current_month).first()
            
            if not usage:
                # Create new usage record for current month
                usage = ApiUsage(
                    month=current_month,
                    requests_used=126,  # Initial value from user requirement
                    requests_limit=2500
                )
                session.add(usage)
                session.commit()
            
            return usage.to_dict()
    
    def increment_api_usage(self, count: int = 1) -> ApiUsage:
        """Increment API usage counter"""
        with self.get_session() as session:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            # Get or create usage record
            usage = session.query(ApiUsage).filter_by(month=current_month).first()
            
            if not usage:
                usage = ApiUsage(
                    month=current_month,
                    requests_used=126  # Initial value
                )
                session.add(usage)
            
            usage.requests_used += count
            usage.updated_at = datetime.utcnow()
            session.commit()
            
            return usage.to_dict()
    
    def reset_api_usage_if_needed(self) -> bool:
        """Reset API usage if it's a new month"""
        with self.get_session() as session:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            # Check all usage records
            all_usage = session.query(ApiUsage).all()
            
            for usage in all_usage:
                if usage.month != current_month:
                    # Archive old month and create new one
                    new_usage = ApiUsage(
                        month=current_month,
                        requests_used=0,
                        requests_limit=2500
                    )
                    session.add(new_usage)
                    session.commit()
                    return True
            
            return False
    
    def can_make_api_request(self, requests_needed: int = 1) -> bool:
        """Check if we can make API requests without exceeding limit"""
        usage = self.get_api_usage()
        remaining = usage['requests_limit'] - usage['requests_used']
        # Leave 100 requests as safety margin
        return remaining > (requests_needed + 100)
    
    def get_api_usage_statistics(self) -> dict:
        """Get comprehensive API usage statistics"""
        with self.get_session() as session:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            # Current month usage
            current = session.query(ApiUsage).filter_by(month=current_month).first()
            
            # Historical usage (last 3 months)
            historical = session.query(ApiUsage)\
                .order_by(ApiUsage.month.desc())\
                .limit(3)\
                .all()
            
            # Calculate daily average for current month
            daily_avg = 0
            if current:
                days_in_month = datetime.utcnow().day
                daily_avg = current.requests_used / days_in_month if days_in_month > 0 else 0
            
            return {
                'current_month': current.to_dict() if current else None,
                'daily_average': round(daily_avg, 1),
                'projected_monthly': round(daily_avg * 30, 0) if daily_avg else 0,
                'history': [usage.to_dict() for usage in historical],
                'warning_level': current.requests_used > 2000 if current else False,
                'critical_level': current.requests_used > 2400 if current else False
            }
    
    def get_trending_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Get trending articles from cache if not expired"""
        with Session(self.engine) as session:
            try:
                cache = session.query(TrendingCache).filter_by(cache_key=cache_key).first()
                if cache and not cache.is_expired():
                    logger.info(f"Trending cache hit for {cache_key}")
                    return cache.articles_data
                elif cache and cache.is_expired():
                    logger.info(f"Trending cache expired for {cache_key}")
                    session.delete(cache)
                    session.commit()
                return None
            except Exception as e:
                logger.error(f"Error getting trending cache: {e}")
                return None
    
    def save_trending_cache(self, cache_key: str, articles: List[Dict]) -> bool:
        """Save trending articles to cache"""
        with Session(self.engine) as session:
            try:
                # Remove old cache if exists
                old_cache = session.query(TrendingCache).filter_by(cache_key=cache_key).first()
                if old_cache:
                    session.delete(old_cache)
                
                # Create new cache entry
                new_cache = TrendingCache(
                    cache_key=cache_key,
                    articles_data=articles
                )
                session.add(new_cache)
                session.commit()
                logger.info(f"Saved trending cache for {cache_key} with {len(articles)} articles")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Error saving trending cache: {e}")
                return False
    
    def clear_expired_trending_cache(self) -> int:
        """Clear expired trending cache entries"""
        with Session(self.engine) as session:
            try:
                expired = session.query(TrendingCache).filter(
                    TrendingCache.expires_at < datetime.utcnow()
                ).all()
                count = len(expired)
                for cache in expired:
                    session.delete(cache)
                session.commit()
                logger.info(f"Cleared {count} expired trending cache entries")
                return count
            except Exception as e:
                session.rollback()
                logger.error(f"Error clearing expired trending cache: {e}")
                return 0
    
    def clear_translated_cache(self, medium_id: str = None) -> int:
        """Clear translated content from cache to force re-translation"""
        with Session(self.engine) as session:
            try:
                if medium_id:
                    # Clear specific article
                    article = session.query(ArticleCache).filter_by(medium_id=medium_id).first()
                    if article:
                        article.translated_content = None
                        article.translated_title = None
                        article.translated_subtitle = None
                        article.is_translated = False
                        session.commit()
                        logger.info(f"Cleared translated cache for article {medium_id}")
                        return 1
                    return 0
                else:
                    # Clear all translated content
                    updated = session.query(ArticleCache).update({
                        ArticleCache.translated_content: None,
                        ArticleCache.translated_title: None,
                        ArticleCache.translated_subtitle: None,
                        ArticleCache.is_translated: False
                    })
                    session.commit()
                    logger.info(f"Cleared translated cache for {updated} articles")
                    return updated
            except Exception as e:
                session.rollback()
                logger.error(f"Error clearing translated cache: {e}")
                raise