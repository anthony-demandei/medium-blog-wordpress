import re
import logging
from typing import Dict, List, Optional
import markdown
from bs4 import BeautifulSoup
import html

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Process and format content for WordPress"""
    
    # Palavras-chave para filtrar artigos indesejados
    BLOCKED_KEYWORDS = [
        'hiring', 'we are hiring', 'job opening', 'job opportunity', 
        'vacancy', 'vaga', 'vagas', 'contratando', 'oportunidade de emprego',
        'sale', 'discount', 'promo', 'promotion', 'black friday',
        'buy now', 'compre agora', 'promoção', 'desconto',
        'iphone', 'samsung galaxy', 'smartphone deals'
    ]
    
    # Tags predefinidas relevantes para Demandei (baseadas nas keywords de busca)
    RELEVANT_TAGS = {
        # DevOps & Cloud
        'kubernetes', 'devops', 'cloud-computing', 'docker', 'ci-cd',
        'aws', 'azure', 'gcp', 'terraform', 'ansible', 'jenkins',
        
        # Automação & Integração
        'n8n', 'api-integration', 'api', 'rest', 'graphql', 'webhook',
        'automation', 'microservices', 'serverless',
        
        # Desenvolvimento Full Stack
        'full-stack', 'full-stack-developer', 'backend-development', 
        'front-end-development', 'frontend', 'backend',
        
        # Frameworks & Libraries
        'nextjs', 'react', 'vue', 'angular', 'laravel', 'spring-boot',
        'django', 'express', 'fastapi', 'rails',
        
        # Linguagens de Programação
        'javascript', 'typescript', 'python', 'java', 'kotlin', 
        'swift', 'golang', 'rust', 'php', 'ruby', 'c#', 'c++',
        'programming-languages', 'programming', 'coding',
        
        # Mobile Development
        'android', 'ios', 'react-native', 'flutter', 'xamarin',
        
        # AI & Machine Learning
        'artificial-intelligence', 'ai', 'deep-learning', 'llm',
        'machine-learning', 'generative-ai', 'generative-ai-tools',
        'chatgpt', 'neural-networks', 'nlp', 'computer-vision',
        
        # Desenvolvimento Web
        'web-development', 'responsive-design', 'pwa', 'spa',
        'web-performance', 'web-security',
        
        # Banco de Dados
        'database', 'postgresql', 'mongodb', 'redis', 'mysql',
        'nosql', 'sql', 'elasticsearch', 'cassandra',
        
        # Outros
        'tech', 'software-development', 'data-science', 'blockchain',
        'cybersecurity', 'iot', 'big-data', 'analytics'
    }
    
    # Mapeamento de categorias
    CATEGORY_MAP = {
        'ai': 'Inteligência Artificial',
        'artificial-intelligence': 'Inteligência Artificial',
        'machine-learning': 'Machine Learning',
        'deep-learning': 'Deep Learning',
        'programming': 'Programação',
        'javascript': 'JavaScript',
        'python': 'Python',
        'react': 'React',
        'nodejs': 'Node.js',
        'web-development': 'Desenvolvimento Web',
        'backend': 'Backend',
        'frontend': 'Frontend',
        'devops': 'DevOps',
        'cloud': 'Cloud Computing',
        'docker': 'Docker',
        'kubernetes': 'Kubernetes',
        'data-science': 'Data Science',
        'database': 'Banco de Dados'
    }
    
    @classmethod
    def should_filter_article(cls, article: Dict) -> bool:
        """Check if article should be filtered out"""
        title = article.get('title', '').lower()
        subtitle = article.get('subtitle', '').lower()
        content = article.get('content', '').lower()[:1000]  # Check first 1000 chars
        
        # Check for blocked keywords
        for keyword in cls.BLOCKED_KEYWORDS:
            if keyword in title or keyword in subtitle or keyword in content:
                logger.info(f"Article filtered due to blocked keyword: {keyword}")
                return True
        
        return False
    
    @classmethod
    def process_markdown_to_html(cls, content: str, content_format: str = 'markdown') -> str:
        """Convert markdown content to properly formatted HTML"""
        if not content:
            return ''
        
        # If content is already in markdown format
        if content_format == 'markdown':
            # Pre-process code blocks for better formatting
            content = cls._preprocess_code_blocks(content)
            
            # Convert markdown to HTML
            md = markdown.Markdown(extensions=[
                'fenced_code',
                'codehilite',
                'tables',
                'nl2br',
                'sane_lists',
                'smarty'
            ])
            html_content = md.convert(content)
            
            # Post-process HTML for WordPress
            html_content = cls._postprocess_html(html_content)
            
        elif content_format == 'html':
            # Clean and process existing HTML
            html_content = cls._postprocess_html(content)
        else:
            # Plain text - convert to basic HTML
            html_content = cls._text_to_html(content)
        
        return html_content
    
    @classmethod
    def _preprocess_code_blocks(cls, content: str) -> str:
        """Preprocess code blocks in markdown for better formatting"""
        # Fix escaped code blocks
        content = re.sub(r'\\`', '`', content)
        content = re.sub(r'\\"', '"', content)
        
        # Ensure proper code block formatting
        content = re.sub(r'```(\w+)\n', r'```\1\n', content)
        
        return content
    
    @classmethod
    def _postprocess_html(cls, html_content: str) -> str:
        """Post-process HTML for WordPress with proper code formatting"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process code blocks
        for code_block in soup.find_all('code'):
            parent = code_block.parent
            
            # Check if it's a code block (inside pre) or inline code
            if parent and parent.name == 'pre':
                # This is a code block
                cls._format_code_block(parent, code_block)
            else:
                # This is inline code
                cls._format_inline_code(code_block)
        
        # Process blockquotes
        for blockquote in soup.find_all('blockquote'):
            cls._format_blockquote(blockquote)
        
        # Process images
        for img in soup.find_all('img'):
            cls._format_image(img)
        
        # Process links
        for link in soup.find_all('a'):
            cls._format_link(link)
        
        return str(soup)
    
    @classmethod
    def _format_code_block(cls, pre_tag, code_tag):
        """Format code blocks with syntax highlighting card"""
        # Get language from class if available
        language = 'python'  # Default language
        if code_tag.get('class'):
            classes = code_tag.get('class')
            for class_name in classes:
                if class_name.startswith('language-'):
                    language = class_name.replace('language-', '')
                    break
        
        # Get code content
        code_content = code_tag.get_text()
        
        # Escape HTML entities
        code_content = html.escape(code_content)
        
        # Create formatted code block with inline header (no line breaks)
        header_html = f'<div style="background: #2d2d2d; padding: 8px 15px; border-bottom: 1px solid #3e3e3e; display: flex; justify-content: space-between; align-items: center;"><span style="color: #a0a0a0; font-size: 12px; font-family: monospace;"><i style="display: inline-block; width: 10px; height: 10px; background: #ff5f56; border-radius: 50%; margin-right: 5px;"></i><i style="display: inline-block; width: 10px; height: 10px; background: #ffbd2e; border-radius: 50%; margin-right: 5px;"></i><i style="display: inline-block; width: 10px; height: 10px; background: #27c93f; border-radius: 50%; margin-right: 10px;"></i>{language.upper()}</span><button onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.innerText)" style="background: #3e3e3e; color: #a0a0a0; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px;">📋 Copiar</button></div>'
        
        formatted_html = f'<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 3px; border-radius: 8px; margin: 20px 0;"><div style="background: #1e1e1e; border-radius: 6px; padding: 0; overflow: hidden;">{header_html}<pre style="margin: 0; padding: 15px; overflow-x: auto; background: #1e1e1e;"><code style="color: #d4d4d4; font-family: \'Consolas\', \'Monaco\', \'Courier New\', monospace; font-size: 14px; line-height: 1.5;">{code_content}</code></pre></div></div>'
        
        # Replace the original pre tag with formatted version
        new_tag = BeautifulSoup(formatted_html, 'html.parser')
        pre_tag.replace_with(new_tag)
    
    @classmethod
    def _format_inline_code(cls, code_tag):
        """Format inline code"""
        code_tag['style'] = 'background-color: #f4f4f4; color: #c7254e; padding: 2px 6px; border-radius: 3px; font-family: monospace; font-size: 90%;'
    
    @classmethod
    def _format_blockquote(cls, blockquote_tag):
        """Format blockquotes"""
        blockquote_tag['style'] = 'border-left: 4px solid #667eea; padding-left: 20px; margin: 20px 0; color: #555; font-style: italic; background: #f9f9f9; padding: 15px 20px; border-radius: 0 8px 8px 0;'
    
    @classmethod
    def _format_image(cls, img_tag):
        """Format images"""
        img_tag['style'] = 'max-width: 100%; height: auto; border-radius: 8px; margin: 20px auto; display: block; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'
        
        # Add loading lazy
        img_tag['loading'] = 'lazy'
    
    @classmethod
    def _format_link(cls, link_tag):
        """Format links"""
        # Add target blank for external links
        href = link_tag.get('href', '')
        if href and href.startswith('http'):
            link_tag['target'] = '_blank'
            link_tag['rel'] = 'noopener noreferrer'
            link_tag['style'] = 'color: #667eea; text-decoration: none; border-bottom: 1px solid #667eea;'
    
    @classmethod
    def _text_to_html(cls, text: str) -> str:
        """Convert plain text to HTML"""
        # Escape HTML
        text = html.escape(text)
        
        # Convert line breaks
        text = text.replace('\n\n', '</p><p>')
        text = text.replace('\n', '<br>')
        
        # Wrap in paragraph tags
        text = f'<p>{text}</p>'
        
        return text
    
    @classmethod
    def filter_and_normalize_tags(cls, tags: List[str]) -> List[str]:
        """Filter and normalize tags to relevant ones"""
        normalized_tags = []
        
        for tag in tags:
            # Normalize tag
            normalized_tag = tag.lower().replace(' ', '-').replace('_', '-')
            
            # Check if tag is relevant
            if normalized_tag in cls.RELEVANT_TAGS:
                normalized_tags.append(normalized_tag)
        
        # Add default tags if none found
        if not normalized_tags:
            normalized_tags = ['tech', 'programming']
        
        # Limit to 5 tags
        return normalized_tags[:5]
    
    @classmethod
    def determine_category(cls, article: Dict) -> str:
        """Determine the best category for an article"""
        tags = article.get('tags', [])
        title = article.get('title', '').lower()
        
        # Check tags for category mapping
        for tag in tags:
            normalized_tag = tag.lower().replace(' ', '-')
            if normalized_tag in cls.CATEGORY_MAP:
                return cls.CATEGORY_MAP[normalized_tag]
        
        # Check title for keywords
        for keyword, category in cls.CATEGORY_MAP.items():
            if keyword in title:
                return category
        
        # Default category
        return 'Tecnologia'
    
    @classmethod
    def clean_attribution_data(cls, article: Dict) -> Dict:
        """Clean attribution data, removing null/empty fields"""
        cleaned_data = {}
        
        # Only include non-empty fields
        if article.get('author'):
            cleaned_data['author'] = article['author']
        
        if article.get('published_at'):
            cleaned_data['published_at'] = article['published_at']
        
        if article.get('reading_time') and article['reading_time'] > 0:
            cleaned_data['reading_time'] = article['reading_time']
        
        if article.get('claps') and article['claps'] > 0:
            cleaned_data['claps'] = article['claps']
        
        if article.get('url'):
            cleaned_data['url'] = article['url']
        
        return cleaned_data