from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import logging
from datetime import datetime
from config import Config
from medium_api import MediumAPI
from wordpress_api import WordPressAPI
from database import Database
from scheduler import SyncScheduler
from translator import GeminiTranslator
from settings_manager import SettingsManager
from cache_manager import CacheManager

logger = logging.getLogger(__name__)

class WebInterface:
    def __init__(self):
        self.app = Flask(__name__, 
                        template_folder='../templates',
                        static_folder='../static')
        self.app.secret_key = Config.SECRET_KEY
        
        # Initialize components
        self.db = Database(Config.DATABASE_PATH)
        self.scheduler = SyncScheduler(Config.TIMEZONE)
        self.settings = SettingsManager()
        self.translator = GeminiTranslator(Config.GEMINI_API_KEY, Config.GEMINI_MODEL)
        self.medium_api = None
        self.wordpress_api = None
        self.cache_manager = None
        
        # Initialize APIs if configured
        self._initialize_apis()
        
        # Initialize cache manager if APIs are available
        if self.medium_api:
            self.cache_manager = CacheManager(self.db, self.medium_api, self.translator)
        
        # Setup routes
        self._setup_routes()
        
        # Set sync function
        self.scheduler.set_sync_function(self.run_sync)
        
        # Start scheduler
        self.scheduler.start()
        
        # Check automation settings and schedule if enabled
        automation_settings = self.db.get_automation_settings()
        if automation_settings.get('automation_enabled', True) and Config.RAPIDAPI_KEY and Config.WORDPRESS_URL:
            self.scheduler.schedule_daily_sync(
                Config.SCHEDULE_HOUR,
                Config.SCHEDULE_MINUTE
            )
    
    def _initialize_apis(self):
        """Initialize APIs if credentials are available"""
        if Config.RAPIDAPI_KEY:
            self.medium_api = MediumAPI(Config.RAPIDAPI_KEY, Config.RAPIDAPI_HOST, self.db)
        
        if Config.WORDPRESS_URL and Config.WORDPRESS_USERNAME and Config.WORDPRESS_PASSWORD:
            self.wordpress_api = WordPressAPI(
                Config.WORDPRESS_URL,
                Config.WORDPRESS_USERNAME,
                Config.WORDPRESS_PASSWORD,
                Config.AUTHOR_NAME
            )
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            # Get statistics
            stats = self.db.get_statistics()
            recent_articles = self.db.get_recent_articles(5)
            sync_logs = self.db.get_sync_logs(5)
            next_sync = self.scheduler.get_next_run_time()
            
            # Get API usage statistics
            api_usage = self.db.get_api_usage()
            api_stats = self.db.get_api_usage_statistics()
            
            # Check configuration status
            config_errors = Config.validate()
            is_configured = len(config_errors) == 0
            
            return render_template('index.html',
                                 stats=stats,
                                 recent_articles=recent_articles,
                                 sync_logs=sync_logs,
                                 next_sync=next_sync,
                                 api_usage=api_usage,
                                 api_stats=api_stats,
                                 is_configured=is_configured,
                                 config_errors=config_errors,
                                 config=Config)
        
        @self.app.route('/sync', methods=['POST'])
        def manual_sync():
            try:
                result = self.run_sync()
                flash(f"Sync completed: {result['synced']} articles synced, {result['skipped']} skipped", 'success')
            except Exception as e:
                flash(f"Sync failed: {str(e)}", 'error')
                logger.error(f"Manual sync failed: {e}")
            
            return redirect(url_for('index'))
        
        @self.app.route('/api/sync', methods=['POST'])
        def api_sync():
            try:
                result = self.run_sync()
                return jsonify({'success': True, 'result': result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/status')
        def api_status():
            stats = self.db.get_statistics()
            next_sync = self.scheduler.get_next_run_time()
            jobs = self.scheduler.get_jobs()
            
            return jsonify({
                'stats': stats,
                'next_sync': next_sync,
                'scheduled_jobs': jobs,
                'is_configured': len(Config.validate()) == 0
            })
        
        @self.app.route('/api/usage')
        def api_usage():
            """Get API usage statistics"""
            usage = self.db.get_api_usage()
            stats = self.db.get_api_usage_statistics()
            
            return jsonify({
                'usage': usage,
                'statistics': stats,
                'can_sync': self.db.can_make_api_request(Config.MAX_ARTICLES_PER_RUN * 2)
            })
        
        @self.app.route('/api/articles')
        def api_articles():
            limit = request.args.get('limit', 10, type=int)
            articles = self.db.get_recent_articles(limit)
            return jsonify({'articles': articles})
        
        @self.app.route('/api/logs')
        def api_logs():
            limit = request.args.get('limit', 10, type=int)
            logs = self.db.get_sync_logs(limit)
            return jsonify({'logs': logs})
        
        @self.app.route('/settings')
        def settings():
            categories = []
            if self.wordpress_api:
                try:
                    categories = self.wordpress_api.get_categories()
                except:
                    pass
            
            settings_data = self.settings.get_all()
            automation_settings = self.db.get_automation_settings()
            
            return render_template('settings.html',
                                 settings=settings_data,
                                 categories=categories,
                                 automation_enabled=automation_settings.get('automation_enabled', True))
        
        @self.app.route('/settings/save', methods=['POST'])
        def save_settings():
            try:
                data = request.get_json()
                self.settings.save_settings(data)
                
                # Reinitialize APIs with new settings
                self._initialize_apis()
                
                # Reschedule if needed
                if data.get('schedule', {}).get('enabled'):
                    hour = data['schedule']['hour']
                    minute = data['schedule']['minute']
                    self.scheduler.reschedule_sync(hour, minute)
                
                return jsonify({'success': True, 'message': 'Settings saved successfully'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/settings/reset', methods=['POST'])
        def reset_settings():
            try:
                self.settings.reset_to_defaults()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/settings/export')
        def export_settings():
            return jsonify(self.settings.get_all())
        
        @self.app.route('/settings/import', methods=['POST'])
        def import_settings():
            try:
                data = request.get_json()
                self.settings.save_settings(data)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/test-connection', methods=['POST'])
        def test_connection():
            results = {
                'medium': False,
                'wordpress': False
            }
            
            # Test Medium API
            if self.medium_api:
                try:
                    # Try a simple search
                    articles = self.medium_api.search_articles('python', limit=1)
                    results['medium'] = len(articles) > 0
                except:
                    results['medium'] = False
            
            # Test WordPress API
            if self.wordpress_api:
                results['wordpress'] = self.wordpress_api.test_connection()
            
            return jsonify(results)
        
        @self.app.route('/search')
        def search():
            query = request.args.get('query', '')
            articles = []
            
            if query:
                # Only make API request if there's a new search query
                if self.cache_manager and self.db.can_make_api_request(1):
                    # Search and cache articles
                    articles = self.cache_manager.search_and_cache(query, limit=12)
                    flash(f'Found {len(articles)} articles for "{query}"', 'success')
                else:
                    # API limit reached, search in cached articles only
                    articles = self.db.get_all_cached_articles()
                    # Filter cached articles by query
                    filtered = []
                    for article in articles:
                        title = (article.get('original_title') or '').lower()
                        subtitle = (article.get('original_subtitle') or '').lower()
                        if query.lower() in title or query.lower() in subtitle:
                            filtered.append(article)
                    articles = filtered
                    flash(f'API limit reached. Showing {len(articles)} cached results', 'info')
            else:
                # No query - show all cached articles without API request
                articles = self.db.get_all_cached_articles()
                flash(f'Showing {len(articles)} cached articles (no API request)', 'info')
            
            return render_template('search.html',
                                 query=query,
                                 articles=articles)
        
        @self.app.route('/trending')
        def trending():
            tag = request.args.get('tag', 'programming')
            mode = request.args.get('mode', 'hot')
            
            # Create cache key for this specific request
            cache_key = f"trending_{tag}_{mode}"
            
            # First check if we have cached data
            articles = self.db.get_trending_cache(cache_key)
            
            if articles is None:
                # No cache or expired, fetch from API
                if self.medium_api and self.db.can_make_api_request(1):
                    articles = self.medium_api.get_trending_articles(tag=tag, mode=mode, limit=12)
                    # Save to trending cache for 24 hours
                    if articles:
                        self.db.save_trending_cache(cache_key, articles)
                    # Also cache individual articles
                    if self.cache_manager:
                        for article in articles:
                            self.cache_manager.cache_article(article)
                else:
                    articles = []
                    flash('API limit reached or Medium API not available', 'warning')
            else:
                # Using cached data - no API request made
                flash(f'Using cached trending data (saves API requests)', 'info')
            
            return render_template('trending.html',
                                 tag=tag,
                                 mode=mode,
                                 articles=articles)
        
        @self.app.route('/topics')
        def topics():
            topic = request.args.get('topic', 'artificial-intelligence')
            
            articles = []
            if self.medium_api:
                articles = self.medium_api.get_latest_posts(topic=topic, limit=12)
                # Cache topic articles
                if self.cache_manager:
                    for article in articles:
                        self.cache_manager.cache_article(article)
            
            return render_template('topics.html',
                                 topic=topic,
                                 articles=articles)
        
        @self.app.route('/compare/<medium_id>')
        def compare(medium_id):
            comparison = None
            
            if self.cache_manager:
                comparison = self.cache_manager.get_comparison_data(medium_id)
            
            return render_template('compare.html',
                                 comparison=comparison)
        
        @self.app.route('/api/translate/<medium_id>', methods=['POST'])
        def api_translate(medium_id):
            try:
                if not self.cache_manager:
                    return jsonify({'success': False, 'error': 'Cache manager not initialized'}), 500
                
                result = self.cache_manager.translate_cached_article(medium_id)
                if result:
                    return jsonify({'success': True, 'message': 'Article translated successfully'})
                else:
                    return jsonify({'success': False, 'error': 'Translation failed'}), 500
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/publish/<medium_id>', methods=['POST'])
        def api_publish(medium_id):
            try:
                if not self.wordpress_api or not self.cache_manager:
                    return jsonify({'success': False, 'error': 'WordPress not configured'}), 500
                
                # Get article from cache
                cached = self.db.get_cache(medium_id)
                if not cached:
                    return jsonify({'success': False, 'error': 'Article not found in cache'}), 404
                
                # Prepare article data for WordPress
                article_data = {
                    'id': medium_id,
                    'title': cached.get('translated_title') or cached.get('original_title'),
                    'subtitle': cached.get('translated_subtitle') or cached.get('original_subtitle'),
                    'content': cached.get('translated_content') or cached.get('original_content'),
                    'author': cached.get('author'),
                    'image_url': cached.get('cover_image'),
                    'url': cached.get('url'),
                    'tags': cached.get('tags', []),
                    'translated': cached.get('is_translated', False)
                }
                
                # Create WordPress post
                result = self.wordpress_api.create_post(
                    article_data,
                    Config.CATEGORY_NAME,
                    Config.POST_STATUS
                )
                
                if result:
                    # Save to articles table
                    self.db.save_article(article_data, result)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Article published successfully',
                        'wordpress_url': result.get('link')
                    })
                else:
                    return jsonify({'success': False, 'error': 'Failed to create WordPress post'}), 500
                    
            except Exception as e:
                logger.error(f"Error publishing article: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/cache/clear', methods=['POST'])
        def api_clear_cache():
            try:
                count = self.db.clear_expired_cache()
                return jsonify({'success': True, 'count': count})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/automation/toggle', methods=['POST'])
        def api_toggle_automation():
            try:
                data = request.get_json()
                enabled = data.get('enabled', True)
                
                # Update database
                self.db.set_automation_enabled(enabled)
                
                # Update scheduler
                if enabled:
                    self.scheduler.schedule_daily_sync(
                        Config.SCHEDULE_HOUR,
                        Config.SCHEDULE_MINUTE
                    )
                    message = 'Automation enabled'
                else:
                    self.scheduler.pause_sync()
                    message = 'Automation disabled'
                
                return jsonify({'success': True, 'message': message, 'enabled': enabled})
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
    
    def run_sync(self) -> dict:
        """Run the synchronization process"""
        if not self.medium_api or not self.wordpress_api:
            raise Exception("APIs not configured. Please check your .env file.")
        
        logger.info("Starting sync process...")
        
        articles_found = 0
        articles_synced = 0
        articles_skipped = 0
        errors = []
        
        try:
            # Search for articles
            articles = self.medium_api.search_articles_by_keywords(
                Config.SEARCH_KEYWORDS,
                Config.MAX_ARTICLES_PER_RUN
            )
            
            articles_found = len(articles)
            logger.info(f"Found {articles_found} articles")
            
            # Filter by language if needed
            if Config.LANGUAGE_PREFERENCE != 'both':
                articles = self.medium_api.filter_articles_by_language(
                    articles,
                    Config.LANGUAGE_PREFERENCE
                )
            
            # Process each article
            for article in articles:
                try:
                    # Check if already synced
                    if self.db.article_exists(article['id']):
                        logger.info(f"Article already synced: {article['title']}")
                        articles_skipped += 1
                        continue
                    
                    # Check if relevant
                    if not self.medium_api.is_article_relevant(article, Config.SEARCH_KEYWORDS):
                        logger.info(f"Article not relevant: {article['title']}")
                        articles_skipped += 1
                        continue
                    
                    # Translate article if configured
                    if Config.AUTO_TRANSLATE and self.translator.enabled:
                        logger.info(f"Translating article: {article['title']}")
                        article = self.translator.translate_article(article, target_lang='pt')
                    
                    # Create WordPress post
                    wordpress_result = self.wordpress_api.create_post(
                        article,
                        Config.CATEGORY_NAME,
                        Config.POST_STATUS
                    )
                    
                    if wordpress_result:
                        # Save to database
                        self.db.save_article(article, wordpress_result)
                        articles_synced += 1
                        logger.info(f"Article synced: {article['title']}")
                    else:
                        errors.append(f"Failed to create post for: {article['title']}")
                        articles_skipped += 1
                        
                except Exception as e:
                    error_msg = f"Error processing article {article.get('title', 'Unknown')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    articles_skipped += 1
            
            # Create sync log
            error_text = '\n'.join(errors) if errors else None
            self.db.create_sync_log(articles_found, articles_synced, articles_skipped, error_text)
            
            result = {
                'found': articles_found,
                'synced': articles_synced,
                'skipped': articles_skipped,
                'errors': errors
            }
            
            logger.info(f"Sync completed: {result}")
            return result
            
        except Exception as e:
            error_msg = f"Sync process failed: {str(e)}"
            logger.error(error_msg)
            self.db.create_sync_log(0, 0, 0, error_msg)
            raise
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the Flask application"""
        self.app.run(host=host, port=port, debug=debug)