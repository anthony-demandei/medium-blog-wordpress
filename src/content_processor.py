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
    
    # Mapeamento de tags para português
    TAG_TRANSLATION_MAP = {
        # Programming Languages
        'javascript': 'JavaScript',
        'python': 'Python',
        'java': 'Java',
        'typescript': 'TypeScript',
        'php': 'PHP',
        'ruby': 'Ruby',
        'golang': 'Go',
        'rust': 'Rust',
        'kotlin': 'Kotlin',
        'swift': 'Swift',
        'c++': 'C++',
        'c#': 'C#',
        
        # Development
        'programming': 'Programação',
        'coding': 'Codificação',
        'software-development': 'Desenvolvimento de Software',
        'web-development': 'Desenvolvimento Web',
        'mobile-development': 'Desenvolvimento Mobile',
        'frontend': 'Frontend',
        'backend': 'Backend',
        'full-stack': 'Full Stack',
        'api': 'API',
        'rest-api': 'API REST',
        'graphql': 'GraphQL',
        
        # Frameworks & Libraries
        'react': 'React',
        'angular': 'Angular',
        'vue': 'Vue.js',
        'nextjs': 'Next.js',
        'nodejs': 'Node.js',
        'express': 'Express.js',
        'django': 'Django',
        'flask': 'Flask',
        'spring': 'Spring',
        'laravel': 'Laravel',
        'rails': 'Ruby on Rails',
        
        # DevOps & Cloud
        'devops': 'DevOps',
        'docker': 'Docker',
        'kubernetes': 'Kubernetes',
        'aws': 'AWS',
        'azure': 'Azure',
        'google-cloud': 'Google Cloud',
        'cloud-computing': 'Computação em Nuvem',
        'ci-cd': 'CI/CD',
        'microservices': 'Microsserviços',
        'serverless': 'Serverless',
        
        # Database
        'database': 'Banco de Dados',
        'sql': 'SQL',
        'nosql': 'NoSQL',
        'mongodb': 'MongoDB',
        'postgresql': 'PostgreSQL',
        'mysql': 'MySQL',
        'redis': 'Redis',
        
        # AI & Data
        'artificial-intelligence': 'Inteligência Artificial',
        'ai': 'IA',
        'machine-learning': 'Aprendizado de Máquina',
        'deep-learning': 'Aprendizado Profundo',
        'data-science': 'Ciência de Dados',
        'data-analysis': 'Análise de Dados',
        'big-data': 'Big Data',
        'neural-networks': 'Redes Neurais',
        'nlp': 'PLN',
        
        # Others
        'technology': 'Tecnologia',
        'tech': 'Tech',
        'tutorial': 'Tutorial',
        'tips': 'Dicas',
        'best-practices': 'Melhores Práticas',
        'performance': 'Desempenho',
        'security': 'Segurança',
        'testing': 'Testes',
        'debugging': 'Depuração',
        'optimization': 'Otimização',
        'architecture': 'Arquitetura',
        'design-patterns': 'Padrões de Design',
        'clean-code': 'Código Limpo',
        'refactoring': 'Refatoração',
        'agile': 'Ágil',
        'scrum': 'Scrum',
        'git': 'Git',
        'github': 'GitHub',
        'open-source': 'Código Aberto',
        'startup': 'Startup',
        'productivity': 'Produtividade',
        'automation': 'Automação'
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
            
            # Pre-process markdown for better structure
            content = cls._preprocess_markdown_structure(content)
            
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
    def _preprocess_markdown_structure(cls, content: str) -> str:
        """Preprocess markdown to ensure good structure"""
        # Ensure headers are H2 not H1
        content = re.sub(r'^# ', '## ', content, flags=re.MULTILINE)
        
        # Ensure proper spacing around headers
        content = re.sub(r'\n(#{2,6} )', r'\n\n\1', content)
        content = re.sub(r'(#{2,6} [^\n]+)\n', r'\1\n\n', content)
        
        # Ensure lists have proper formatting
        content = re.sub(r'^([*+-]) ', r'\1 ', content, flags=re.MULTILINE)
        
        # Remove excessive blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    @classmethod
    def _postprocess_html(cls, html_content: str) -> str:
        """Post-process HTML for WordPress with proper code formatting"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process headers - ensure they are H2
        for h1 in soup.find_all('h1'):
            h1.name = 'h2'
        
        # Process headers - no styling, just clean H2
        for header in soup.find_all(['h2', 'h3', 'h4']):
            # Remove any inline styles
            if header.get('style'):
                del header['style']
            # Ensure H2 headers don't have extra styling
            if header.name == 'h2':
                header.clear()
                header.string = header.get_text()
        
        # Process paragraphs - clean formatting
        for p in soup.find_all('p'):
            # Remove empty paragraphs except for spacers
            if not p.get_text(strip=True) and not p.find('br'):
                if p.get_text() != ' ':  # Keep &nbsp; paragraphs
                    p.decompose()
                    continue
        
        # Process lists - ensure clean formatting
        for ul in soup.find_all('ul'):
            if ul.get('style'):
                del ul['style']
        
        for li in soup.find_all('li'):
            if li.get('style'):
                del li['style']
        
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
        
        # Add HR tags between major sections
        # This is done by checking for H2 headers
        h2_tags = soup.find_all('h2')
        for i, h2 in enumerate(h2_tags):
            if i > 0:  # Don't add before the first H2
                # Create HR element
                hr = soup.new_tag('hr')
                # Insert before the H2
                h2.insert_before(hr)
        
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
        
        # Create formatted code block without buttons (cleaner for WordPress)
        formatted_html = f'''<div class="codehilite">
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 3px; border-radius: 8px; margin: 20px 0;">
<div style="background: #1e1e1e; border-radius: 6px; padding: 0; overflow: hidden;">
<pre style="margin: 0; padding: 15px; overflow-x: auto; background: #1e1e1e;"><code style="color: #d4d4d4; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 14px; line-height: 1.5;">{code_content}</code></pre>
</div>
</div>
</div>'''
        
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
        # Use simpler styling for WordPress
        blockquote_tag['style'] = 'border-left: 4px solid #667eea; padding-left: 20px; margin: 20px 0; color: #555; font-style: italic;'
    
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