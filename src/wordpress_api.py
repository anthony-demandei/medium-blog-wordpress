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
    
    def get_recent_posts(self, limit: int = 5) -> List[Dict]:
        """Get recent posts from WordPress"""
        try:
            response = requests.get(
                f"{self.api_url}/posts",
                headers=self.headers,
                params={
                    'per_page': limit,
                    'orderby': 'date',
                    'order': 'desc',
                    '_embed': True  # Include featured media and author info
                }
            )
            
            if response.status_code == 200:
                posts = response.json()
                formatted_posts = []
                
                for post in posts:
                    formatted_post = {
                        'id': post.get('id'),
                        'title': post.get('title', {}).get('rendered', ''),
                        'excerpt': post.get('excerpt', {}).get('rendered', ''),
                        'date': post.get('date'),
                        'link': post.get('link'),
                        'author': self._get_author_name(post),
                        'featured_image': self._get_featured_image(post),
                        'categories': self._get_categories(post)
                    }
                    formatted_posts.append(formatted_post)
                
                return formatted_posts
            else:
                logger.error(f"Failed to fetch posts: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching WordPress posts: {e}")
            return []
    
    def _get_author_name(self, post: Dict) -> str:
        """Extract author name from embedded data"""
        try:
            if '_embedded' in post and 'author' in post['_embedded']:
                return post['_embedded']['author'][0].get('name', 'Unknown')
        except:
            pass
        return 'Unknown'
    
    def _get_featured_image(self, post: Dict) -> Optional[str]:
        """Extract featured image URL from embedded data"""
        try:
            if '_embedded' in post and 'wp:featuredmedia' in post['_embedded']:
                media = post['_embedded']['wp:featuredmedia'][0]
                return media.get('source_url')
        except:
            pass
        return None
    
    def _get_categories(self, post: Dict) -> List[str]:
        """Extract category names from embedded data"""
        categories = []
        try:
            if '_embedded' in post and 'wp:term' in post['_embedded']:
                for term_type in post['_embedded']['wp:term']:
                    for term in term_type:
                        if term.get('taxonomy') == 'category':
                            categories.append(term.get('name', ''))
        except:
            pass
        return categories
    
    def create_post(self, article: Dict, category_name: str = 'Technology', status: str = 'draft', translator=None) -> Optional[Dict]:
        """Create a new WordPress post from Medium article"""
        try:
            # Get or create category
            category_id = self.get_or_create_category(category_name)
            
            # Prepare post content
            post_data = self._prepare_post_data(article, category_id, status)
            
            # Create the post with timeout
            logger.info("Creating WordPress post...")
            response = requests.post(
                f"{self.api_url}/posts",
                json=post_data,
                headers=self.headers,
                timeout=30
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
        
        # Add featured image if available or generate one
        image_url = article.get('image_url') or article.get('cover_image')
        
        if image_url:
            # Upload existing image to WordPress Media Library
            media_id = self.upload_image_from_url(image_url, article.get('title', ''))
            if media_id:
                post_data['featured_media'] = media_id
                logger.info(f"Featured image set: {media_id}")
        elif translator and hasattr(translator, 'generate_cover_image'):
            # No image available, generate one
            logger.info("No cover image found, generating one...")
            image_bytes = translator.generate_cover_image(
                title=article.get('title', 'Article'),
                subtitle=article.get('subtitle', ''),
                tags=article.get('tags', [])
            )
            
            if image_bytes:
                # Upload generated image
                media_id = self.upload_image_bytes(
                    image_bytes, 
                    f"cover-{article.get('id', 'generated')}.png",
                    article.get('title', '')
                )
                if media_id:
                    post_data['featured_media'] = media_id
                    logger.info(f"Generated featured image set: {media_id}")
            else:
                logger.warning("Failed to generate cover image")
        
        return post_data
    
    def _format_content(self, article: Dict) -> str:
        """Format article content for WordPress with proper code formatting"""
        content = article.get('content', '')
        content_format = article.get('content_format', 'markdown')
        
        # Process content through ContentProcessor
        processed_content = ContentProcessor.process_markdown_to_html(content, content_format)
        
        # Add initial space like WordPress posts
        formatted_content = '<p>&nbsp;</p>\n'
        
        # Add subtitle if exists
        subtitle = article.get('subtitle', '')
        if subtitle and not subtitle.lower() in content.lower()[:200]:
            formatted_content += f'<p style="font-size: 1.1em; color: #555; line-height: 1.6; margin-bottom: 25px;">{subtitle}</p>\n'
        
        # Add horizontal separator
        formatted_content += '<hr />\n\n'
        
        # Add the main content
        formatted_content += processed_content
        
        return formatted_content
    
    def upload_image_bytes(self, image_bytes: bytes, filename: str, alt_text: str = '') -> Optional[int]:
        """Upload image bytes to WordPress Media Library"""
        try:
            # Prepare headers for upload
            upload_headers = self.headers.copy()
            upload_headers['Content-Type'] = 'image/png'
            upload_headers['Content-Disposition'] = f'attachment; filename={filename}'
            
            # Upload to WordPress with timeout
            logger.info(f"Uploading generated image: {filename}")
            upload_response = requests.post(
                f"{self.api_url}/media",
                data=image_bytes,
                headers=upload_headers,
                timeout=30
            )
            
            if upload_response.status_code == 201:
                media = upload_response.json()
                logger.info(f"Generated image uploaded successfully: {media.get('id')}")
                return media.get('id')
            else:
                logger.error(f"Failed to upload generated image: {upload_response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading generated image: {e}")
            return None
    
    def upload_image_from_url(self, image_url: str, alt_text: str = '') -> Optional[int]:
        """Upload an image from URL to WordPress Media Library"""
        try:
            # Download image with timeout
            logger.info(f"Downloading image from: {image_url[:50]}...")
            response = requests.get(image_url, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to download image: {image_url}")
                return None
            
            # Get filename from URL
            filename = image_url.split('/')[-1].split('?')[0]
            if not filename or '.' not in filename:
                filename = 'featured-image.jpg'
            
            # Prepare headers for upload
            upload_headers = self.headers.copy()
            upload_headers['Content-Type'] = 'image/jpeg'
            upload_headers['Content-Disposition'] = f'attachment; filename={filename}'
            
            # Upload to WordPress with timeout
            logger.info("Uploading image to WordPress...")
            upload_response = requests.post(
                f"{self.api_url}/media",
                data=response.content,
                headers=upload_headers,
                timeout=30
            )
            
            if upload_response.status_code == 201:
                media = upload_response.json()
                logger.info(f"Image uploaded successfully: {media.get('id')}")
                return media.get('id')
            else:
                logger.error(f"Failed to upload image: {upload_response.status_code} - {upload_response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return None
    
    def _prepare_tags(self, tags: List[str]) -> List[int]:
        """Convert tag names to WordPress tag IDs with Portuguese translation"""
        tag_ids = []
        
        # Limit to 3 tags to speed up the process
        for tag_name in tags[:3]:
            # Translate tag to Portuguese if mapping exists
            translated_tag = ContentProcessor.TAG_TRANSLATION_MAP.get(tag_name.lower(), tag_name)
            
            # Log translation for debugging
            if translated_tag != tag_name:
                logger.info(f"Translated tag: '{tag_name}' -> '{translated_tag}'")
            
            tag_id = self._get_or_create_tag(translated_tag)
            if tag_id:
                tag_ids.append(tag_id)
                
            # Stop if we already have 3 tags
            if len(tag_ids) >= 3:
                break
        
        logger.info(f"Prepared {len(tag_ids)} tags for WordPress")
        return tag_ids
    
    def _get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """Get existing tag ID or create new tag"""
        try:
            # Search for existing tag with timeout
            response = requests.get(
                f"{self.api_url}/tags",
                headers=self.headers,
                params={'search': tag_name, 'per_page': 1},
                timeout=10
            )
            
            if response.status_code == 200:
                tags = response.json()
                if tags:
                    logger.info(f"Found existing tag '{tag_name}': {tags[0].get('id')}")
                    return tags[0].get('id')
            
            # Create new tag if not found
            logger.info(f"Creating new tag: {tag_name}")
            response = requests.post(
                f"{self.api_url}/tags",
                json={'name': tag_name},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 201:
                tag = response.json()
                logger.info(f"Tag created successfully: {tag_name} - ID: {tag.get('id')}")
                return tag.get('id')
            else:
                logger.warning(f"Failed to create tag '{tag_name}': {response.status_code}")
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while handling tag '{tag_name}'")
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