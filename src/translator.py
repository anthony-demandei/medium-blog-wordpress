import logging
import os
from typing import Optional, Dict, Tuple
import google.generativeai as genai
from bs4 import BeautifulSoup
import re
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random

logger = logging.getLogger(__name__)

class GeminiTranslator:
    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            try:
                self.model = genai.GenerativeModel(self.model_name)
                self.enabled = True
                logger.info(f"Gemini translator initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model {self.model_name}: {e}")
                # Fallback to default model
                try:
                    self.model = genai.GenerativeModel('gemini-pro')
                    self.enabled = True
                    logger.info("Fallback to gemini-pro model")
                except:
                    self.model = None
                    self.enabled = False
                    logger.error("Failed to initialize any Gemini model")
        else:
            self.model = None
            self.enabled = False
            logger.warning("Gemini API key not configured. Translation will be disabled.")
    
    def translate_and_rewrite(self, content: str, source_lang: str = 'en', target_lang: str = 'pt') -> str:
        """Translate and rewrite content to avoid plagiarism"""
        if not self.enabled:
            logger.info("Translation disabled - returning original content")
            return content
        
        try:
            # Check if content is markdown (has code blocks)
            has_code_blocks = '```' in content or '`' in content
            
            if has_code_blocks:
                # Process content preserving code blocks
                return self._translate_with_code_preservation(content, source_lang, target_lang)
            
            # Extract HTML structure if present
            soup = BeautifulSoup(content, 'html.parser')
            is_html = bool(soup.find())
            
            if is_html:
                # Process HTML content preserving structure
                return self._translate_html(content, source_lang, target_lang)
            else:
                # Process plain text
                return self._translate_text(content, source_lang, target_lang)
                
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return content
    
    def _translate_with_code_preservation(self, content: str, source_lang: str, target_lang: str) -> str:
        """Translate content while preserving code blocks exactly"""
        # Extract code blocks
        code_blocks = []
        code_pattern = r'```[\s\S]*?```|`[^`\n]+`'
        
        def replace_code(match):
            code_blocks.append(match.group(0))
            return f'__CODE_BLOCK_{len(code_blocks)-1}__'
        
        # Replace code blocks with placeholders
        content_without_code = re.sub(code_pattern, replace_code, content)
        
        # Translate the text without code
        translated = self._translate_text(content_without_code, source_lang, target_lang)
        
        # Restore code blocks
        for i, code_block in enumerate(code_blocks):
            translated = translated.replace(f'__CODE_BLOCK_{i}__', code_block)
        
        return translated
    
    def _translate_html(self, html_content: str, source_lang: str, target_lang: str) -> str:
        """Translate HTML content preserving structure and media"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all text nodes
        for element in soup.find_all(text=True):
            if element.parent.name not in ['script', 'style', 'code', 'pre']:
                text = element.strip()
                if text and len(text) > 10:  # Only translate substantial text
                    translated = self._translate_text(text, source_lang, target_lang)
                    element.replace_with(translated)
        
        return str(soup)
    
    def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate and rewrite plain text"""
        if not text or len(text.strip()) < 10:
            return text
        
        try:
            # Prepare prompt for translation and rewriting
            lang_map = {
                'en': 'English',
                'pt': 'Portuguese',
                'es': 'Spanish',
                'fr': 'French'
            }
            
            source_language = lang_map.get(source_lang, 'English')
            target_language = lang_map.get(target_lang, 'Portuguese')
            
            prompt = f"""
            Você é um tradutor profissional de conteúdo técnico especializado em desenvolvimento de software e artigos de tecnologia para a plataforma Demandei.
            
            CONTEXTO DEMANDEI:
            A Demandei é uma plataforma inteligente que conecta empresas a desenvolvedores, designers e especialistas digitais. Com IA assistida, microserviços, talentos verificados e segurança total no pagamento. A plataforma oferece:
            - Detalhamento automático de projetos com IA
            - Divisão em microserviços com especialistas qualificados
            - Pagamento liberado apenas após aprovação
            - Comissão justa (mínima 5%, primeira 3,9%)
            
            PÚBLICO-ALVO:
            - Freelancers e desenvolvedores brasileiros
            - Empresas que buscam contratar talentos tech
            - Profissionais de tecnologia em geral
            
            REGRAS OBRIGATÓRIAS DE TRADUÇÃO:
            
            1. SEMPRE escreva em TERCEIRA PESSOA representando a Demandei
            
            2. CONVERSÕES OBRIGATÓRIAS (NUNCA use primeira/segunda pessoa):
               ❌ "você pode" → ✅ "o desenvolvedor pode", "a empresa pode", "profissionais podem"
               ❌ "seu projeto" → ✅ "o projeto", "projetos da equipe"
               ❌ "você deve" → ✅ "é recomendado", "desenvolvedores devem"
               ❌ "sua aplicação" → ✅ "a aplicação", "aplicações da empresa"
               ❌ "você precisa" → ✅ "é necessário", "freelancers precisam"
               ❌ "seu código" → ✅ "o código", "código do projeto"
               
            3. SEMPRE referencie os seguintes termos:
               - "freelancers", "desenvolvedores", "empresas", "equipes técnicas"
               - "profissionais", "especialistas", "talentos verificados"
               - "clientes", "projetos", "demandas"
            
            4. Mencione naturalmente o contexto Demandei (2-3 vezes no texto):
               - "Na plataforma Demandei, profissionais encontram..."
               - "Empresas que buscam talentos na Demandei..."
               - "Freelancers especializados conectados através da Demandei..."
               - "Para projetos complexos, a Demandei facilita..."
               - "Desenvolvedores cadastrados na plataforma..."
            
            5. PRESERVE EXATAMENTE (não traduza):
               - Nomes de linguagens: Python, JavaScript, Java, Kotlin, Laravel
               - Frameworks: React, Next.js, Angular, Vue.js, Spring Boot
               - Tecnologias: Docker, Kubernetes, N8n, API, REST
               - Ferramentas: Git, GitHub, VS Code
               - Código, variáveis, funções, URLs
               - Siglas técnicas: AI, LLM, DevOps, CI/CD
            
            6. TOM E ESTILO:
               - Profissional mas acessível
               - Educativo e informativo
               - Focado em valor para a comunidade tech
               - Evite jargões desnecessários
            
            7. ESTRUTURA:
               - Mantenha parágrafos concisos
               - Use subtítulos quando apropriado
               - Preserve formatação de código
               - Adicione contexto brasileiro quando relevante
            
            8. PONTUAÇÃO:
               - NUNCA use hífen (–) para separar ideias
               - Use vírgulas, pontos ou dois pontos para conectar frases
               - Prefira frases mais diretas sem travessões
               - Exemplo: ❌ "Esta funcionalidade – que é muito útil – permite..."
               - Exemplo: ✅ "Esta funcionalidade, que é muito útil, permite..."
            
            VALIDAÇÃO FINAL:
            ✓ Texto TOTALMENTE em terceira pessoa
            ✓ Zero uso de "você", "seu", "sua"
            ✓ Menções naturais à Demandei
            ✓ Termos técnicos preservados
            ✓ Fluidez em português brasileiro
            ✓ SEM uso de hífen (–) para separar ideias
            
            Traduza de {source_language} para {target_language} brasileiro:
            
            {text}
            
            IMPORTANTE: Forneça APENAS o texto traduzido em terceira pessoa. Sem explicações ou metadados.
            """
            
            response = self.model.generate_content(prompt)
            translated_text = response.text.strip()
            
            # Clean up any potential formatting issues
            translated_text = self._clean_translated_text(translated_text)
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Text translation error: {e}")
            return text
    
    def _clean_translated_text(self, text: str) -> str:
        """Clean up translated text"""
        # Remove any potential prompt leakage
        text = re.sub(r'^(Translated text:|Translation:|Here is|Here\'s|Aqui está|Texto traduzido).*?:', '', text, flags=re.IGNORECASE)
        
        # Remove standalone words that shouldn't exist
        problem_words = ['Refresh', 'Reload', 'Update', 'Click here']
        for word in problem_words:
            # Only remove if it's a standalone line or paragraph
            text = re.sub(rf'^{word}\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
            text = re.sub(rf'\n{word}\s*\n', '\n', text, flags=re.IGNORECASE)
        
        # Remove related articles sections and author references
        text = self._remove_related_content(text)
        
        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = text.strip()
        
        # Remove hyphens used for parenthetical expressions
        text = self._remove_hyphens(text)
        
        # Validate that the text makes sense
        if len(text) < 10 or text.count(' ') < 3:
            # Text is too short or doesn't have enough words
            logger.warning(f"Translation might be incomplete: {text[:50]}")
        
        return text
    
    def _remove_related_content(self, text: str) -> str:
        """Remove related articles sections and author references from text"""
        # Patterns for related articles sections
        related_patterns = [
            r'Leia mais artigos relacionados:.*?(?=\n\n|\Z)',
            r'Read more articles:.*?(?=\n\n|\Z)',
            r'Artigos relacionados:.*?(?=\n\n|\Z)',
            r'Related articles:.*?(?=\n\n|\Z)',
            r'Veja também:.*?(?=\n\n|\Z)',
            r'See also:.*?(?=\n\n|\Z)',
            r'Confira também:.*?(?=\n\n|\Z)',
            r'Check out:.*?(?=\n\n|\Z)',
            r'Outros artigos:.*?(?=\n\n|\Z)',
            r'Other articles:.*?(?=\n\n|\Z)',
        ]
        
        for pattern in related_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove specific article titles that look like recommendations
        article_patterns = [
            r'Como este jovem de \d+ anos faturou.*?\n',
            r'Estas \d+ ferramentas.*?mudaram.*?\n',
            r'Gastei.*?antes de perceber.*?\n',
            r'These \d+ tools.*?changed.*?\n',
            r'I spent.*?before realizing.*?\n',
            r'How this.*?year old made.*?\n',
        ]
        
        for pattern in article_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove author signatures and social media references
        author_patterns = [
            r'\n.*?\|\s*SuperFast\s*\|.*?(?:\n|$)',
            r'\n.*?\|\s*Twitter.*?\|.*?(?:\n|$)',
            r'\n.*?\|\s*X\s*\|.*?(?:\n|$)',
            r'\n.*?\|\s*LinkedIn\s*\|.*?(?:\n|$)',
            r'\n.*?\|\s*GitHub\s*\|.*?(?:\n|$)',
            r'\n.*?\|\s*Medium\s*\|.*?(?:\n|$)',
            r'\nKalash Vasaniya.*?(?:\n|$)',
            r'\n@\w+\s*(?:\n|$)',  # Remove Twitter handles
            r'\nFollow me on.*?(?:\n|$)',
            r'\nSiga-me no.*?(?:\n|$)',
            r'\nConnect with me.*?(?:\n|$)',
            r'\nConecte-se comigo.*?(?:\n|$)',
        ]
        
        for pattern in author_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove lines that are just author names or social media
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip lines that are just names or social media
            if not re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+\s*$', line.strip()) and \
               not re.match(r'^.*?(Twitter|LinkedIn|GitHub|Medium|Instagram|Facebook|X)\s*\(?.*?\)?\s*$', line.strip(), re.IGNORECASE):
                cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        return text
    
    def _remove_hyphens(self, text: str) -> str:
        """Remove hyphens used for parenthetical expressions and replace with commas"""
        # Replace em dash (–) and en dash (—) patterns used for parenthetical expressions
        # Pattern: " – text – " becomes " , text, "
        text = re.sub(r'\s+[–—]\s+([^–—]+?)\s+[–—]\s+', r', \1, ', text)
        
        # Replace single em dash at beginning of parenthetical: " – text"
        text = re.sub(r'\s+[–—]\s+([^.!?]+)', r', \1', text)
        
        # Replace patterns like "text – that is important"
        text = re.sub(r'(\w+)\s+[–—]\s+([^.!?]+)', r'\1, \2', text)
        
        # Clean up double commas that might result
        text = re.sub(r',\s*,', ',', text)
        
        # Clean up comma before period
        text = re.sub(r',\s*\.', '.', text)
        
        return text
    
    def _translate_title(self, title: str, source_lang: str, target_lang: str) -> str:
        """Translate title with specific instructions for clean, concise titles"""
        if not title or len(title.strip()) < 3:
            return title
        
        try:
            lang_map = {
                'en': 'English',
                'pt': 'Portuguese',
                'es': 'Spanish',
                'fr': 'French'
            }
            
            source_language = lang_map.get(source_lang, 'English')
            target_language = lang_map.get(target_lang, 'Portuguese')
            
            prompt = f"""
            Você é um especialista em tradução de títulos para artigos técnicos.
            
            INSTRUÇÕES ESPECÍFICAS PARA TÍTULOS:
            1. Traduza APENAS o título de {source_language} para {target_language} brasileiro
            2. Mantenha o título CONCISO e DIRETO (máximo 80 caracteres)
            3. Use terceira pessoa (sem "você", "seu", "sua")
            4. Preserve números, anos, e termos técnicos exatamente
            5. NÃO adicione subtítulos, descrições ou explicações
            6. NÃO use dois pontos (:) desnecessários
            7. Foque na ideia principal do título
            8. Mantenha o mesmo tom do original (informativo, técnico, etc.)
            
            EXEMPLOS:
            ❌ "10 Repositórios Python para 2025: Para Desenvolvedores que Buscam..."
            ✅ "10 Repositórios Python Essenciais para 2025"
            
            ❌ "Como Configurar Docker: Um Guia Completo para Iniciantes"
            ✅ "Como Configurar Docker: Guia Completo"
            
            TÍTULO ORIGINAL:
            {title}
            
            RESPOSTA (apenas o título traduzido):
            """
            
            response = self.model.generate_content(prompt)
            translated_title = response.text.strip()
            
            # Clean up any extra text that might have been added
            translated_title = self._clean_title(translated_title)
            
            # Remove hyphens from title
            translated_title = self._remove_hyphens(translated_title)
            
            return translated_title
            
        except Exception as e:
            logger.error(f"Title translation error: {e}")
            return title
    
    def _clean_title(self, title: str) -> str:
        """Clean translated title removing unwanted additions"""
        # Remove common prefixes that might be added
        title = re.sub(r'^(Título traduzido:|Resposta:|Here is|Aqui está).*?:', '', title, flags=re.IGNORECASE)
        
        # Remove quotes if the entire title is wrapped in them
        title = title.strip()
        if (title.startswith('"') and title.endswith('"')) or (title.startswith("'") and title.endswith("'")):
            title = title[1:-1]
        
        # Limit title length for WordPress compatibility
        if len(title) > 100:
            title = title[:97] + '...'
        
        return title.strip()
    
    def generate_cover_image(self, title: str, subtitle: str = "", tags: list = None) -> Optional[bytes]:
        """Generate a cover image for articles without one"""
        try:
            # Try to use Gemini 2.0 Flash experimental for image generation
            try:
                import google.genai as genai_new
                client = genai_new.Client(api_key=self.api_key)
                
                # Create a prompt for image generation
                prompt = f"""
                Create a professional, modern blog cover image for an article about:
                Title: {title}
                Subtitle: {subtitle or 'Technology article'}
                Topics: {', '.join(tags[:3]) if tags else 'technology, programming'}
                
                Style: Clean, minimalist, tech-focused, gradient background, abstract geometric shapes.
                No text in the image. Professional blog header style.
                """
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt,
                    config=genai_new.types.GenerateContentConfig(
                        response_modalities=['IMAGE']
                    )
                )
                
                if response and response.candidates:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'image') and part.image:
                            # Return image bytes
                            return part.image.data
                            
            except Exception as e:
                logger.warning(f"Gemini image generation failed: {e}, falling back to placeholder")
            
            # Fallback: Generate a placeholder image with Pillow
            return self._generate_placeholder_image(title, subtitle, tags)
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None
    
    def _generate_placeholder_image(self, title: str, subtitle: str = "", tags: list = None) -> bytes:
        """Generate a placeholder image when API generation fails"""
        # Image dimensions (WordPress featured image size)
        width, height = 1200, 630
        
        # Create image with gradient background
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        # Generate gradient based on category/tags
        colors = [
            ((102, 126, 234), (118, 75, 162)),  # Purple gradient
            ((10, 132, 255), (48, 209, 88)),    # Blue-green gradient  
            ((255, 159, 10), (255, 45, 85)),    # Orange-red gradient
            ((50, 215, 75), (10, 132, 255)),    # Green-blue gradient
            ((175, 82, 222), (255, 45, 85)),    # Purple-red gradient
        ]
        
        # Select color based on content
        color_index = hash(title) % len(colors)
        start_color, end_color = colors[color_index]
        
        # Draw gradient background
        for y in range(height):
            ratio = y / height
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
        
        # Add semi-transparent overlay
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 60))
        img.paste(overlay, (0, 0), overlay)
        
        # Add geometric shapes for visual interest
        for _ in range(3):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(100, 300)
            opacity = random.randint(10, 30)
            shape_overlay = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            shape_draw = ImageDraw.Draw(shape_overlay)
            shape_draw.ellipse([x-size, y-size, x+size, y+size], fill=(255, 255, 255, opacity))
            img = Image.alpha_composite(img.convert('RGBA'), shape_overlay).convert('RGB')
        
        # Try to use a font, fallback to default if not available
        try:
            # Try to use a system font
            font_size = 48
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except:
            # Use default font
            font = ImageFont.load_default()
            small_font = font
        
        # Add title text
        # Wrap text if too long
        max_width = width - 100
        words = title.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            if draw.textlength(test_line, font=font) > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw title
        y_text = height // 2 - (len(lines) * 30)
        for line in lines[:3]:  # Max 3 lines
            text_width = draw.textlength(line, font=font)
            x_text = (width - text_width) // 2
            # Draw shadow
            draw.text((x_text + 2, y_text + 2), line, font=font, fill=(0, 0, 0, 128))
            # Draw text
            draw.text((x_text, y_text), line, font=font, fill=(255, 255, 255))
            y_text += 60
        
        # Add subtitle if provided
        if subtitle:
            subtitle_width = draw.textlength(subtitle[:60], font=small_font)
            x_subtitle = (width - subtitle_width) // 2
            draw.text((x_subtitle, y_text + 20), subtitle[:60], font=small_font, fill=(255, 255, 255, 200))
        
        # Add watermark
        watermark = "demandei.com.br"
        watermark_width = draw.textlength(watermark, font=small_font)
        draw.text((width - watermark_width - 20, height - 40), watermark, font=small_font, fill=(255, 255, 255, 128))
        
        # Convert to bytes
        img_byte_array = BytesIO()
        img.save(img_byte_array, format='PNG', optimize=True)
        return img_byte_array.getvalue()
    
    def translate_article(self, article: Dict, target_lang: str = 'pt') -> Dict:
        """Translate entire article preserving structure"""
        if not self.enabled:
            return article
        
        try:
            # Detect source language
            source_lang = article.get('lang', 'en')
            
            # Skip if already in target language
            if source_lang == target_lang:
                logger.info(f"Article already in {target_lang}, skipping translation")
                return article
            
            # Translate title with specific instruction for clean titles
            if article.get('title'):
                article['title'] = self._translate_title(
                    article['title'], 
                    source_lang, 
                    target_lang
                )
            
            # Translate subtitle
            if article.get('subtitle'):
                article['subtitle'] = self._translate_text(
                    article['subtitle'], 
                    source_lang, 
                    target_lang
                )
            
            # Translate content
            if article.get('content'):
                article['content'] = self.translate_and_rewrite(
                    article['content'],
                    source_lang,
                    target_lang
                )
            
            # Update language
            article['lang'] = target_lang
            article['translated'] = True
            
            logger.info(f"Article translated from {source_lang} to {target_lang}")
            return article
            
        except Exception as e:
            logger.error(f"Article translation error: {e}")
            return article
    
    def summarize_content(self, content: str, max_length: int = 500) -> str:
        """Create a summary of the content"""
        if not self.enabled:
            # Simple truncation if Gemini not available
            return content[:max_length] + '...' if len(content) > max_length else content
        
        try:
            prompt = f"""
            Create a concise summary of the following content in Portuguese.
            The summary should be no more than {max_length} characters.
            Focus on the main points and key information.
            
            Content:
            {content[:2000]}  # Limit input to avoid token limits
            
            Provide ONLY the summary, without any explanation.
            """
            
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            
            if len(summary) > max_length:
                summary = summary[:max_length-3] + '...'
            
            return summary
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return content[:max_length] + '...' if len(content) > max_length else content