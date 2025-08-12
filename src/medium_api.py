import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time
from content_processor import ContentProcessor

logger = logging.getLogger(__name__)

class MediumAPI:
    def __init__(self, api_key: str, api_host: str, database=None):
        self.api_key = api_key
        self.api_host = api_host
        self.base_url = f"https://{api_host}"
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": api_host
        }
        self.database = database
    
    def search_articles(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for articles on Medium"""
        try:
            url = f"{self.base_url}/search/articles"
            params = {"query": query}
            
            logger.info(f"Searching Medium API for: {query}")
            
            # Track API usage
            if self.database:
                self.database.increment_api_usage(1)
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            # API returns 'articles' not 'article_ids'
            article_ids = data.get('articles', data.get('article_ids', []))[:limit]
            
            if not article_ids:
                logger.warning(f"No articles found for query: {query}")
                return []
            
            logger.info(f"Found {len(article_ids)} article IDs")
            
            articles = []
            for i, article_id in enumerate(article_ids):
                logger.info(f"Fetching article {i+1}/{len(article_ids)}: {article_id}")
                article_data = self.get_article_info(article_id)
                if article_data:
                    # Filter out unwanted content
                    if not ContentProcessor.should_filter_article(article_data):
                        articles.append(article_data)
                    else:
                        logger.info(f"Article filtered: {article_data.get('title', 'Unknown')}")
                time.sleep(0.5)  # Rate limiting
            
            logger.info(f"Successfully fetched {len(articles)} articles")
            return articles
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout searching for: {query}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching articles: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in search: {e}")
            return []
    
    def get_article_info(self, article_id: str) -> Optional[Dict]:
        """Get detailed information about an article"""
        try:
            url = f"{self.base_url}/article/{article_id}"
            
            # Track API usage
            if self.database:
                self.database.increment_api_usage(1)
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant information
            article_info = {
                'id': article_id,
                'title': data.get('title', ''),
                'subtitle': data.get('subtitle', ''),
                'author': data.get('author', ''),
                'author_id': data.get('author_id', ''),
                'publication_id': data.get('publication_id', ''),
                'published_at': data.get('published_at', ''),
                'url': data.get('url', ''),
                'tags': data.get('tags', []),
                'topics': data.get('topics', []),
                'claps': data.get('claps', 0),
                'responses_count': data.get('responses_count', 0),
                'reading_time': data.get('reading_time', 0),
                'word_count': data.get('word_count', 0),
                'image_url': data.get('image_url', ''),
                'lang': data.get('lang', 'en')
            }
            
            # Get article content in markdown format for better formatting
            try:
                content = self.get_article_content(article_id, format='markdown')
                if content:
                    article_info['content'] = content
                    article_info['content_format'] = 'markdown'
                else:
                    # Fallback to HTML if markdown fails
                    content = self.get_article_content(article_id, format='html')
                    if content:
                        article_info['content'] = content
                        article_info['content_format'] = 'html'
            except Exception as e:
                logger.warning(f"Could not get content for article {article_id}: {e}")
                article_info['content'] = ''
                article_info['content_format'] = 'none'
            
            return article_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting article info for {article_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting article {article_id}: {e}")
            return None
    
    def get_article_content(self, article_id: str, format: str = 'markdown') -> Optional[str]:
        """Get the full content of an article in specified format"""
        try:
            # Use markdown by default for better formatting
            if format == 'markdown':
                url = f"{self.base_url}/article/{article_id}/markdown"
            elif format == 'html':
                url = f"{self.base_url}/article/{article_id}/html"
            else:
                url = f"{self.base_url}/article/{article_id}/content"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Different response keys based on format
            if format == 'markdown':
                return data.get('markdown', '')
            elif format == 'html':
                return data.get('html', '')
            else:
                return data.get('content', '')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting article {format} for {article_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting {format} for {article_id}: {e}")
            return None
    
    def search_articles_by_keywords(self, keywords: List[str], max_articles: int = 5) -> List[Dict]:
        """Search articles using multiple keywords"""
        all_articles = []
        seen_ids = set()
        
        for keyword in keywords:
            logger.info(f"Searching for keyword: {keyword}")
            articles = self.search_articles(keyword, limit=max_articles)
            
            for article in articles:
                if article['id'] not in seen_ids:
                    seen_ids.add(article['id'])
                    all_articles.append(article)
            
            if len(all_articles) >= max_articles:
                break
            
            time.sleep(1)  # Rate limiting between searches
        
        # Sort by publication date (most recent first)
        all_articles.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        return all_articles[:max_articles]
    
    def get_trending_articles(self, tag: str = 'programming', mode: str = 'hot', limit: int = 10) -> List[Dict]:
        """Get trending/hot/new articles for a specific tag
        
        Modes:
        - hot: Trending articles
        - new: Latest articles
        - top_year: Best articles of the year
        - top_month: Best articles of the month
        - top_week: Best articles of the week
        - top_all_time: Best articles overall
        """
        try:
            url = f"{self.base_url}/topfeeds/{tag}/{mode}"
            
            logger.info(f"Fetching {mode} articles for tag: {tag}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            article_ids = data.get('topfeeds', [])[:limit]
            
            if not article_ids:
                logger.warning(f"No {mode} articles found for tag: {tag}")
                return []
            
            logger.info(f"Found {len(article_ids)} {mode} article IDs")
            
            articles = []
            for i, article_id in enumerate(article_ids):
                logger.info(f"Fetching article {i+1}/{len(article_ids)}: {article_id}")
                article_data = self.get_article_info(article_id)
                if article_data:
                    # Filter out unwanted content
                    if not ContentProcessor.should_filter_article(article_data):
                        article_data['trending_type'] = mode
                        article_data['trending_tag'] = tag
                        articles.append(article_data)
                    else:
                        logger.info(f"Trending article filtered: {article_data.get('title', 'Unknown')}")
                time.sleep(0.5)  # Rate limiting
            
            return articles
            
        except Exception as e:
            logger.error(f"Error getting trending articles: {e}")
            return []
    
    def get_latest_posts(self, topic: str, limit: int = 10) -> List[Dict]:
        """Get latest posts for a specific topic (returns 25 by default from API)"""
        try:
            url = f"{self.base_url}/latestposts/{topic}"
            
            logger.info(f"Fetching latest posts for topic: {topic}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            article_ids = data.get('latestposts', [])[:limit]
            
            if not article_ids:
                logger.warning(f"No latest posts found for topic: {topic}")
                return []
            
            articles = []
            for i, article_id in enumerate(article_ids):
                logger.info(f"Fetching article {i+1}/{len(article_ids)}: {article_id}")
                article_data = self.get_article_info(article_id)
                if article_data:
                    article_data['topic'] = topic
                    articles.append(article_data)
                time.sleep(0.5)  # Rate limiting
            
            return articles
            
        except Exception as e:
            logger.error(f"Error getting latest posts: {e}")
            return []
    
    def get_related_articles(self, article_id: str) -> List[Dict]:
        """Get related articles for a specific article"""
        try:
            url = f"{self.base_url}/article/{article_id}/related"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            related_ids = data.get('related_articles', [])
            
            if not related_ids:
                return []
            
            articles = []
            for rel_id in related_ids[:4]:  # Limit to 4 related articles
                article_data = self.get_article_info(rel_id)
                if article_data:
                    articles.append(article_data)
                time.sleep(0.5)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error getting related articles: {e}")
            return []
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get detailed user/author information"""
        try:
            url = f"{self.base_url}/user/{user_id}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'id': data.get('id'),
                'username': data.get('username'),
                'fullname': data.get('fullname'),
                'bio': data.get('bio'),
                'followers_count': data.get('followers_count', 0),
                'following_count': data.get('following_count', 0),
                'image_url': data.get('image_url'),
                'twitter_username': data.get('twitter_username'),
                'is_writer_program_enrolled': data.get('is_writer_program_enrolled', False),
                'medium_member_at': data.get('medium_member_at'),
                'top_writer_in': data.get('top_writer_in', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return None
    
    def filter_articles_by_language(self, articles: List[Dict], language: str) -> List[Dict]:
        """Filter articles by language preference"""
        if language == 'both':
            return articles
        
        filtered = []
        for article in articles:
            article_lang = article.get('lang', 'en')
            
            if language == 'pt' and article_lang in ['pt', 'pt-BR']:
                filtered.append(article)
            elif language == 'en' and article_lang == 'en':
                filtered.append(article)
        
        return filtered
    
    def is_article_relevant(self, article: Dict, keywords: List[str]) -> bool:
        """Check if an article is relevant based on keywords"""
        title = article.get('title', '').lower()
        subtitle = article.get('subtitle', '').lower()
        tags = [tag.lower() for tag in article.get('tags', [])]
        topics = [topic.lower() for topic in article.get('topics', [])]
        
        # Check if any keyword appears in title, subtitle, tags, or topics
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if (keyword_lower in title or 
                keyword_lower in subtitle or 
                keyword_lower in tags or 
                keyword_lower in topics):
                return True
        
        return False