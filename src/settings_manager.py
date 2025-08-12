import json
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class SettingsManager:
    def __init__(self, settings_file: str = 'data/settings.json'):
        self.settings_file = settings_file
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file or create default"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    logger.info("Settings loaded from file")
                    return settings
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
        
        # Return default settings if file doesn't exist
        return self.get_default_settings()
    
    def save_settings(self, settings: Dict[str, Any] = None) -> bool:
        """Save settings to JSON file"""
        if settings:
            self.settings = settings
        
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info("Settings saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default settings"""
        return {
            'medium_api': {
                'rapidapi_key': os.getenv('RAPIDAPI_KEY', ''),
                'rapidapi_host': os.getenv('RAPIDAPI_HOST', 'medium2.p.rapidapi.com')
            },
            'wordpress': {
                'url': os.getenv('WORDPRESS_URL', ''),
                'username': os.getenv('WORDPRESS_USERNAME', ''),
                'password': os.getenv('WORDPRESS_PASSWORD', ''),
                'author_name': os.getenv('AUTHOR_NAME', 'Demandei'),
                'default_category': os.getenv('CATEGORY_NAME', 'Technology'),
                'post_status': os.getenv('POST_STATUS', 'draft')
            },
            'gemini': {
                'api_key': os.getenv('GEMINI_API_KEY', ''),
                'enabled': os.getenv('AUTO_TRANSLATE', 'true').lower() == 'true'
            },
            'search': {
                'keywords': os.getenv('SEARCH_KEYWORDS', '').split(',') if os.getenv('SEARCH_KEYWORDS') else [
                    'python', 'javascript', 'react', 'nodejs', 'AI', 'machine learning'
                ],
                'max_articles': int(os.getenv('MAX_ARTICLES_PER_RUN', 2)),
                'language_preference': os.getenv('LANGUAGE_PREFERENCE', 'both'),
                'min_claps': 0,
                'recent_days': 30
            },
            'schedule': {
                'enabled': True,
                'hour': int(os.getenv('SCHEDULE_HOUR', 8)),
                'minute': int(os.getenv('SCHEDULE_MINUTE', 0)),
                'timezone': os.getenv('TIMEZONE', 'America/Sao_Paulo')
            },
            'content': {
                'auto_translate': os.getenv('AUTO_TRANSLATE', 'true').lower() == 'true',
                'target_language': 'pt',
                'preserve_formatting': True,
                'add_source_link': True,
                'add_author_credit': True
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get setting value by dot notation path"""
        keys = key_path.split('.')
        value = self.settings
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> bool:
        """Set setting value by dot notation path"""
        keys = key_path.split('.')
        settings = self.settings
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in settings:
                settings[key] = {}
            settings = settings[key]
        
        # Set the value
        settings[keys[-1]] = value
        return self.save_settings()
    
    def update_section(self, section: str, data: Dict[str, Any]) -> bool:
        """Update entire section of settings"""
        if section in self.settings:
            self.settings[section].update(data)
        else:
            self.settings[section] = data
        
        return self.save_settings()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings"""
        return self.settings.copy()
    
    def reset_to_defaults(self) -> bool:
        """Reset settings to defaults"""
        self.settings = self.get_default_settings()
        return self.save_settings()
    
    def validate_settings(self) -> Dict[str, List[str]]:
        """Validate current settings and return errors/warnings"""
        errors = []
        warnings = []
        
        # Check Medium API
        if not self.get('medium_api.rapidapi_key'):
            errors.append("RapidAPI key is missing")
        
        # Check WordPress
        if not self.get('wordpress.url'):
            errors.append("WordPress URL is missing")
        if not self.get('wordpress.username'):
            errors.append("WordPress username is missing")
        if not self.get('wordpress.password'):
            errors.append("WordPress password is missing")
        
        # Check Gemini (optional)
        if self.get('content.auto_translate') and not self.get('gemini.api_key'):
            warnings.append("Translation enabled but Gemini API key is missing")
        
        # Check search keywords
        keywords = self.get('search.keywords', [])
        if not keywords or (isinstance(keywords, list) and len(keywords) == 0):
            errors.append("No search keywords configured")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }
    
    def export_settings(self) -> str:
        """Export settings as JSON string"""
        return json.dumps(self.settings, indent=2, ensure_ascii=False)
    
    def import_settings(self, json_string: str) -> bool:
        """Import settings from JSON string"""
        try:
            settings = json.loads(json_string)
            self.settings = settings
            return self.save_settings()
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False