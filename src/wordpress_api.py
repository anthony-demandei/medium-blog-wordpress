import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime
import html2text
import base64
from content_processor import ContentProcessor

logger = logging.getLogger(__name__)

class WordPressAPI:
    def __init__(self, url: str, username: str, password: str, author_name: str = 'Demandei'):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.author_name = author_name
        self.api_url = f"{self.url}/wp-json/wp/v2"
        
        # Create auth header
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> bool:
        """Test if WordPress connection is working"""
        try:
            response = requests.get(
                f"{self.api_url}/posts",
                headers=self.headers,
                params={'per_page': 1}
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"WordPress connection test failed: {e}")
            return False
    
    def create_post(self, article: Dict, category_name: str = 'Technology', status: str = 'draft') -> Optional[Dict]:
        """Create a new WordPress post from Medium article"""
        try:
            # Get or create category
            category_id = self.get_or_create_category(category_name)
            
            # Prepare post content
            post_data = self._prepare_post_data(article, category_id, status)
            
            # Create the post
            response = requests.post(
                f"{self.api_url}/posts",
                json=post_data,
                headers=self.headers
            )
            
            if response.status_code == 201:
                post = response.json()
                logger.info(f"Post created successfully: {post.get('link')}")
                return {
                    'id': post.get('id'),
                    'link': post.get('link'),
                    'status': post.get('status')
                }
            else:
                logger.error(f"Failed to create post: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating WordPress post: {e}")
            return None
    
    def _prepare_post_data(self, article: Dict, category_id: int, status: str) -> Dict:
        """Prepare post data for WordPress"""
        # Convert content to HTML if needed
        content = self._format_content(article)
        
        # Create excerpt
        excerpt = article.get('subtitle', '')
        if not excerpt and article.get('content'):
            # Create excerpt from first 150 characters of content
            h = html2text.HTML2Text()
            h.ignore_links = True
            text_content = h.handle(article.get('content', ''))
            excerpt = text_content[:150] + '...' if len(text_content) > 150 else text_content
        
        # Filter and normalize tags
        filtered_tags = ContentProcessor.filter_and_normalize_tags(article.get('tags', []))
        tags = self._prepare_tags(filtered_tags)
        
        # Create post data
        post_data = {
            'title': article.get('title', 'Untitled'),
            'content': content,
            'excerpt': excerpt,
            'status': status,
            'categories': [category_id],
            'tags': tags,
            'format': 'standard',
            'meta': {
                'medium_article_id': article.get('id', ''),
                'medium_author': article.get('author', ''),
                'medium_url': article.get('url', ''),
                'medium_published_at': article.get('published_at', '')
            }
        }
        
        # Add featured image if available
        if article.get('image_url'):
            # This would require uploading the image first
            # For now, we'll embed it in the content
            pass
        
        return post_data
    
    def _format_content(self, article: Dict) -> str:
        """Format article content for WordPress with proper code formatting"""
        content = article.get('content', '')
        content_format = article.get('content_format', 'markdown')
        
        # Process content through ContentProcessor
        processed_content = ContentProcessor.process_markdown_to_html(content, content_format)
        
        # Add featured image if available
        featured_image = ''
        if article.get('image_url'):
            featured_image = f'''
            <div style="margin-bottom: 30px; text-align: center;">
                <img src="{article["image_url"]}" 
                     alt="{article.get("title", "")}" 
                     style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            </div>
            '''
        
        # Add attribution header with cleaned data
        attribution = self._create_attribution(article)
        
        # Format the complete content
        formatted_content = f"""
        {featured_image}
        
        {attribution}
        
        <div style="margin: 30px 0; border-top: 2px solid #e0e0e0;"></div>
        
        {processed_content}
        
        <div style="margin: 30px 0; border-top: 2px solid #e0e0e0;"></div>
        
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 3px; border-radius: 10px; margin: 30px 0;">
            <div style="background: white; padding: 20px; border-radius: 8px;">
                <h4 style="margin-top: 0; color: #333;">💡 Sobre este artigo</h4>
                <p style="color: #666;">Este conteúdo foi adaptado e traduzido para português brasileiro pela equipe <strong>Demandei</strong>, 
                plataforma que conecta freelancers e empresas de tecnologia.</p>
                <p style="margin-bottom: 0;">
                    <a href="{article.get('url', '#')}" target="_blank" rel="noopener" 
                       style="color: #667eea; text-decoration: none; font-weight: bold;">
                       📖 Leia o artigo original no Medium →
                    </a>
                </p>
            </div>
        </div>
        """
        
        return formatted_content
    
    def _create_attribution(self, article: Dict) -> str:
        """Create attribution section for the post"""
        # Removed attribution section - content is presented as native Demandei content
        return ''
    
    def _prepare_tags(self, tags: List[str]) -> List[int]:
        """Convert tag names to WordPress tag IDs"""
        tag_ids = []
        
        for tag_name in tags[:5]:  # Limit to 5 tags
            tag_id = self._get_or_create_tag(tag_name)
            if tag_id:
                tag_ids.append(tag_id)
        
        return tag_ids
    
    def _get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """Get existing tag ID or create new tag"""
        try:
            # Search for existing tag
            response = requests.get(
                f"{self.api_url}/tags",
                headers=self.headers,
                params={'search': tag_name, 'per_page': 1}
            )
            
            if response.status_code == 200:
                tags = response.json()
                if tags:
                    return tags[0].get('id')
            
            # Create new tag if not found
            response = requests.post(
                f"{self.api_url}/tags",
                json={'name': tag_name},
                headers=self.headers
            )
            
            if response.status_code == 201:
                tag = response.json()
                return tag.get('id')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error handling tag '{tag_name}': {e}")
        
        return None
    
    def get_categories(self) -> List[Dict]:
        """Get all categories from WordPress"""
        try:
            response = requests.get(
                f"{self.api_url}/categories",
                headers=self.headers,
                params={'per_page': 100}
            )
            
            if response.status_code == 200:
                categories = response.json()
                return [
                    {
                        'id': cat.get('id'),
                        'name': cat.get('name'),
                        'slug': cat.get('slug')
                    }
                    for cat in categories
                ]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting categories: {e}")
        
        return []
    
    def get_or_create_category(self, category_name: str = None, article: Dict = None) -> int:
        """Get or create category based on article content"""
        # Determine category from article if not provided
        if not category_name and article:
            category_name = ContentProcessor.determine_category(article)
        elif not category_name:
            category_name = 'Tecnologia'
        
        return self._get_or_create_category_id(category_name)
    
    def _get_or_create_category_id(self, category_name: str) -> int:
        """Get existing category ID or create new category"""
        try:
            # First, try to find existing category
            response = requests.get(
                f"{self.api_url}/categories",
                headers=self.headers,
                params={'search': category_name, 'per_page': 1}
            )
            
            if response.status_code == 200:
                categories = response.json()
                if categories:
                    logger.info(f"Found existing category: {category_name}")
                    return categories[0].get('id')
            
            # Create new category if not found
            logger.info(f"Creating new category: {category_name}")
            response = requests.post(
                f"{self.api_url}/categories",
                json={'name': category_name},
                headers=self.headers
            )
            
            if response.status_code == 201:
                category = response.json()
                logger.info(f"Category created successfully: {category_name}")
                return category.get('id')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error handling category '{category_name}': {e}")
        
        # Return default category ID if all else fails
        return 1
    
    def check_duplicate(self, article_id: str) -> bool:
        """Check if article was already posted"""
        try:
            # Search for posts with the same Medium article ID in meta
            response = requests.get(
                f"{self.api_url}/posts",
                headers=self.headers,
                params={
                    'meta_key': 'medium_article_id',
                    'meta_value': article_id,
                    'per_page': 1
                }
            )
            
            if response.status_code == 200:
                posts = response.json()
                return len(posts) > 0
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking for duplicate: {e}")
        
        return False