import logging
import os
from typing import Optional, Dict
import google.generativeai as genai
from bs4 import BeautifulSoup
import re

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