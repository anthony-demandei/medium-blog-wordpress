from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import re
from contextlib import contextmanager

logger = logging.getLogger(__name__)

Base = declarative_base()

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    medium_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    subtitle = Column(Text)
    content = Column(Text)
    author = Column(String(255))
    image_url = Column(Text)
    url = Column(Text)
    tags = Column(JSON)
    wordpress_id = Column(Integer)
    wordpress_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    synced_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'medium_id': self.medium_id,
            'title': self.title,
            'subtitle': self.subtitle,
            'author': self.author,
            'image_url': self.image_url,
            'url': self.url,
            'tags': self.tags,
            'wordpress_id': self.wordpress_id,
            'wordpress_url': self.wordpress_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None
        }

class SyncLog(Base):
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50))
    articles_found = Column(Integer, default=0)
    articles_synced = Column(Integer, default=0)
    articles_skipped = Column(Integer, default=0)
    errors = Column(Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'articles_found': self.articles_found,
            'articles_synced': self.articles_synced,
            'articles_skipped': self.articles_skipped,
            'errors': self.errors,
            'status': self.status
        }

class ApiUsage(Base):
    __tablename__ = 'api_usage'
    
    id = Column(Integer, primary_key=True)
    month = Column(String(7), unique=True, nullable=False)  # Format: YYYY-MM
    requests_used = Column(Integer, default=0)
    requests_limit = Column(Integer, default=2500)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'month': self.month,
            'requests_used': self.requests_used,
            'requests_limit': self.requests_limit,
            'requests_remaining': self.requests_limit - self.requests_used,
            'usage_percentage': round((self.requests_used / self.requests_limit) * 100, 1),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AutomationSettings(Base):
    __tablename__ = 'automation_settings'
    
    id = Column(Integer, primary_key=True)
    automation_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'automation_enabled': self.automation_enabled,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Database:
    def __init__(self, db_path: str):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database initialized at {db_path}")
    
    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def save_article(self, article_data: dict, wordpress_data: dict = None) -> Article:
        """Save or update an article"""
        with self.get_session() as session:
            # Check if article exists
            existing = session.query(Article).filter_by(medium_id=article_data['id']).first()
            
            if existing:
                # Update existing article
                existing.title = article_data.get('title', existing.title)
                existing.subtitle = article_data.get('subtitle', existing.subtitle)
                existing.content = article_data.get('content', existing.content)
                existing.tags = article_data.get('tags', existing.tags)
                if wordpress_data:
                    existing.wordpress_id = wordpress_data.get('id')
                    existing.wordpress_url = wordpress_data.get('link')
                    existing.synced_at = datetime.utcnow()
                session.commit()
                return existing
            else:
                # Create new article
                article = Article(
                    medium_id=article_data['id'],
                    title=article_data.get('title', ''),
                    subtitle=article_data.get('subtitle', ''),
                    content=article_data.get('content', ''),
                    author=article_data.get('author', ''),
                    image_url=article_data.get('image_url', ''),
                    url=article_data.get('url', ''),
                    tags=article_data.get('tags', [])
                )
                
                if wordpress_data:
                    article.wordpress_id = wordpress_data.get('id')
                    article.wordpress_url = wordpress_data.get('link')
                    article.synced_at = datetime.utcnow()
                
                session.add(article)
                session.commit()
                return article
    
    def article_exists(self, medium_id: str) -> bool:
        """Check if an article already exists"""
        with self.get_session() as session:
            return session.query(Article).filter_by(medium_id=medium_id).first() is not None
    
    def get_recent_articles(self, limit: int = 10) -> list:
        """Get recent articles"""
        with self.get_session() as session:
            articles = session.query(Article)\
                .order_by(Article.created_at.desc())\
                .limit(limit)\
                .all()
            return [article.to_dict() for article in articles]
    
    def get_statistics(self) -> dict:
        """Get database statistics"""
        with self.get_session() as session:
            total_articles = session.query(Article).count()
            synced_articles = session.query(Article).filter(Article.wordpress_id.isnot(None)).count()
            last_sync = session.query(SyncLog).order_by(SyncLog.created_at.desc()).first()
            
            return {
                'total_articles': total_articles,
                'synced_articles': synced_articles,
                'pending_articles': total_articles - synced_articles,
                'last_sync': last_sync.created_at.isoformat() if last_sync else None,
                'sync_success_rate': round((synced_articles / total_articles * 100) if total_articles > 0 else 0, 1)
            }
    
    def create_sync_log(self, articles_found: int = 0, articles_synced: int = 0, 
                       articles_skipped: int = 0, errors: str = None) -> SyncLog:
        """Create a sync log entry"""
        with self.get_session() as session:
            log = SyncLog(
                articles_found=articles_found,
                articles_synced=articles_synced,
                articles_skipped=articles_skipped,
                errors=errors,
                status='success' if not errors else 'error'
            )
            session.add(log)
            session.commit()
            return log
    
    def get_sync_logs(self, limit: int = 10) -> list:
        """Get recent sync logs"""
        with self.get_session() as session:
            logs = session.query(SyncLog)\
                .order_by(SyncLog.created_at.desc())\
                .limit(limit)\
                .all()
            return [log.to_dict() for log in logs]
    
    def get_automation_settings(self) -> dict:
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
    
    def get_api_usage(self) -> dict:
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
    
    def increment_api_usage(self, count: int = 1) -> dict:
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