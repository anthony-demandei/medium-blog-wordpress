import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Medium API
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
    RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST', 'medium2.p.rapidapi.com')
    
    # WordPress
    WORDPRESS_URL = os.getenv('WORDPRESS_URL')
    WORDPRESS_USERNAME = os.getenv('WORDPRESS_USERNAME')
    WORDPRESS_PASSWORD = os.getenv('WORDPRESS_PASSWORD')
    AUTHOR_NAME = os.getenv('AUTHOR_NAME', 'Demandei')
    CATEGORY_NAME = os.getenv('CATEGORY_NAME', 'Technology')
    
    # Google Gemini
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
    
    # Search Settings
    SEARCH_KEYWORDS = [k.strip() for k in os.getenv('SEARCH_KEYWORDS', '').split(',') if k.strip()]
    MAX_ARTICLES_PER_RUN = int(os.getenv('MAX_ARTICLES_PER_RUN', 2))
    LANGUAGE_PREFERENCE = os.getenv('LANGUAGE_PREFERENCE', 'both')
    
    # Schedule
    SCHEDULE_HOUR = int(os.getenv('SCHEDULE_HOUR', 8))
    SCHEDULE_MINUTE = int(os.getenv('SCHEDULE_MINUTE', 0))
    TIMEZONE = os.getenv('TIMEZONE', 'America/Sao_Paulo')
    
    # Content
    AUTO_TRANSLATE = os.getenv('AUTO_TRANSLATE', 'true').lower() == 'true'
    POST_STATUS = os.getenv('POST_STATUS', 'draft')
    CATEGORY_ID = int(os.getenv('CATEGORY_ID', 1)) if os.getenv('CATEGORY_ID') else None
    
    # Database
    DATABASE_PATH = 'data/medium_wordpress.db'
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    @classmethod
    def validate(cls):
        errors = []
        
        if not cls.RAPIDAPI_KEY:
            errors.append("RAPIDAPI_KEY is required")
        
        if not cls.WORDPRESS_URL:
            errors.append("WORDPRESS_URL is required")
        
        if not cls.WORDPRESS_USERNAME:
            errors.append("WORDPRESS_USERNAME is required")
        
        if not cls.WORDPRESS_PASSWORD:
            errors.append("WORDPRESS_PASSWORD is required")
        
        if not cls.SEARCH_KEYWORDS or cls.SEARCH_KEYWORDS == ['']:
            errors.append("At least one SEARCH_KEYWORD is required")
        
        return errors