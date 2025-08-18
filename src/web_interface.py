from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
import logging
from datetime import datetime
from config import Config
from medium_api import MediumAPI
from wordpress_api import WordPressAPI
from database import Database
from scheduler import SyncScheduler
from translator import GeminiTranslator
from settings_manager import SettingsManager
from auth import init_auth, require_auth

logger = logging.getLogger(__name__)

class WebInterface:
    def __init__(self):
        self.app = Flask(__name__, 
                        template_folder='../templates',
                        static_folder='../static')
        self.app.secret_key = Config.SECRET_KEY
        
        # Initialize authentication
        init_auth(self.app)
        
        # Initialize components
        self.db = Database(Config.DATABASE_PATH)
        self.scheduler = SyncScheduler(Config.TIMEZONE)
        self.settings = SettingsManager()
        self.translator = GeminiTranslator(Config.GEMINI_API_KEY, Config.GEMINI_MODEL)
        self.medium_api = None
        self.wordpress_api = None
        
        # Initialize APIs if configured
        self._initialize_apis()
        
        
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
        @login_required
        def index():
            # Get statistics
            stats = self.db.get_statistics()
            
            # Get recent posts from WordPress instead of local DB
            wordpress_posts = []
            if self.wordpress_api:
                try:
                    wordpress_posts = self.wordpress_api.get_recent_posts(10)
                except Exception as e:
                    logger.error(f"Error fetching WordPress posts: {e}")
                    wordpress_posts = []
            
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
                                 recent_articles=wordpress_posts,  # Now using WordPress posts
                                 sync_logs=sync_logs,
                                 next_sync=next_sync,
                                 api_usage=api_usage,
                                 api_stats=api_stats,
                                 is_configured=is_configured,
                                 config_errors=config_errors,
                                 config=Config)
        
        @self.app.route('/sync', methods=['POST'])
        @login_required
        def manual_sync():
            try:
                result = self.run_sync()
                flash(f"Sync completed: {result['synced']} articles synced, {result['skipped']} skipped", 'success')
            except Exception as e:
                flash(f"Sync failed: {str(e)}", 'error')
                logger.error(f"Manual sync failed: {e}")
            
            return redirect(url_for('index'))
        
        @self.app.route('/api/sync', methods=['POST'])
        @login_required
        def api_sync():
            try:
                result = self.run_sync()
                return jsonify({'success': True, 'result': result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/status')
        @login_required
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
        @login_required
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
        @login_required
        def api_articles():
            limit = request.args.get('limit', 10, type=int)
            articles = self.db.get_recent_articles(limit)
            return jsonify({'articles': articles})
        
        @self.app.route('/api/logs')
        @login_required
        def api_logs():
            limit = request.args.get('limit', 10, type=int)
            logs = self.db.get_sync_logs(limit)
            return jsonify({'logs': logs})
        
        @self.app.route('/settings')
        @login_required
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
        @login_required
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
        @login_required
        def reset_settings():
            try:
                self.settings.reset_to_defaults()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/settings/export')
        @login_required
        def export_settings():
            return jsonify(self.settings.get_all())
        
        @self.app.route('/settings/import', methods=['POST'])
        @login_required
        def import_settings():
            try:
                data = request.get_json()
                self.settings.save_settings(data)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/test-connection', methods=['POST'])
        @login_required
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
        
        @self.app.route('/trending')
        @login_required
        def trending():
            tag = request.args.get('tag', '')
            mode = request.args.get('mode', 'hot')
            limit = request.args.get('limit', 6, type=int)
            
            # Ensure limit is between 1 and 6
            limit = max(1, min(6, limit))
            
            articles = []
            searched = bool(tag)  # True if user has submitted a search
            
            if searched:
                # Fetch from API directly (no cache)
                if self.medium_api and self.db.can_make_api_request(1):
                    try:
                        all_articles = self.medium_api.get_trending_articles(tag=tag, mode=mode, limit=limit * 2)  # Fetch more to filter
                        
                        # Filter only articles with cover images
                        articles_with_images = []
                        for article in all_articles:
                            if article and (article.get('cover_image') or article.get('image_url')):
                                articles_with_images.append(article)
                                if len(articles_with_images) >= limit:
                                    break
                        
                        articles = articles_with_images[:limit]
                        
                        if not articles:
                            flash('Nenhum artigo com imagem de capa encontrado. Tente outro tópico.', 'info')
                            
                    except Exception as e:
                        logger.error(f"Error fetching trending articles: {e}")
                        flash('Erro ao buscar artigos. Tente novamente.', 'error')
                else:
                    flash('Limite de API atingido. Tente novamente mais tarde.', 'warning')
            
            return render_template('trending.html',
                                 tag=tag,
                                 mode=mode,
                                 limit=limit,
                                 articles=articles,
                                 searched=searched)
        
        @self.app.route('/topics')
        @login_required
        def topics():
            topic = request.args.get('topic', 'artificial-intelligence')
            
            articles = []
            if self.medium_api:
                articles = self.medium_api.get_latest_posts(topic=topic, limit=12)
            
            return render_template('topics.html',
                                 topic=topic,
                                 articles=articles)
        
        @self.app.route('/compare/<medium_id>')
        @login_required
        def compare(medium_id):
            # Compare route removed - no cache system
            return redirect(url_for('index'))
        
        
        
        
        @self.app.route('/api/automation/toggle', methods=['POST'])
        @login_required
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
        
        @self.app.route('/api/sync_article', methods=['POST'])
        @login_required
        def api_sync_single_article():
            """Sync a single article from Medium to WordPress"""
            try:
                data = request.get_json()
                article_url = data.get('url')
                
                if not article_url:
                    return jsonify({'status': 'error', 'message': 'URL não fornecida'}), 400
                
                if not self.medium_api or not self.wordpress_api:
                    return jsonify({'status': 'error', 'message': 'APIs não configuradas'}), 500
                
                # For now, we need the article data to be passed from the frontend
                # since we removed the cache system
                article = data.get('article')
                
                if not article:
                    # Try to fetch from Medium API if we have the URL
                    if self.medium_api:
                        try:
                            # Extract search term from URL for searching
                            # This is a simplified approach
                            article_title = article_url.split('/')[-1].replace('-', ' ')[:50]
                            articles = self.medium_api.search_articles(article_title, limit=1)
                            if articles:
                                article = articles[0]
                        except Exception as e:
                            logger.error(f"Error fetching article: {e}")
                    
                    if not article:
                        return jsonify({'status': 'error', 'message': 'Artigo não encontrado. Por favor, busque novamente.'})
                
                # Check if article already exists
                article_id = article.get('id')
                if article_id and self.db.article_exists(article_id):
                    return jsonify({'status': 'error', 'message': 'Artigo já foi sincronizado anteriormente'})
                
                # Translate if configured
                if Config.AUTO_TRANSLATE and self.translator.enabled:
                    logger.info(f"Translating article: {article.get('title')}")
                    article = self.translator.translate_article(article, target_lang='pt')
                
                # Get post status from settings
                post_status = self.settings.get('wordpress.post_status', 'draft')
                
                # Create WordPress post (pass translator for image generation)
                wordpress_result = self.wordpress_api.create_post(
                    article,
                    Config.CATEGORY_NAME,
                    post_status,
                    translator=self.translator
                )
                
                if wordpress_result:
                    # Save to database
                    self.db.save_article(article, wordpress_result)
                    return jsonify({
                        'status': 'success',
                        'message': 'Artigo sincronizado com sucesso!',
                        'wordpress_url': wordpress_result.get('link')
                    })
                else:
                    return jsonify({'status': 'error', 'message': 'Falha ao criar post no WordPress'})
                    
            except Exception as e:
                logger.error(f"Error syncing single article: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
    
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
                    
                    # Get post status from settings
                    post_status = self.settings.get('wordpress.post_status', 'draft')
                    
                    # Create WordPress post (pass translator for image generation)
                    wordpress_result = self.wordpress_api.create_post(
                        article,
                        Config.CATEGORY_NAME,
                        post_status,
                        translator=self.translator
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