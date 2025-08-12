# 📝 AI Blog Writer - Artigos & Insights Medium

Sistema automatizado que busca artigos relevantes do Medium, traduz para português brasileiro em terceira pessoa (representando a plataforma Demandei) e publica no WordPress.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Recursos

- 🔍 Busca automática de artigos no Medium via API
- 📝 Publicação automática no WordPress
- ⏰ Agendamento diário configurável
- 🌐 Interface web para monitoramento
- 📊 Histórico de sincronizações
- 🔒 Prevenção de duplicatas
- 🐳 Containerizado com Docker

## Pré-requisitos

- Docker e Docker Compose instalados
- Conta no [RapidAPI](https://rapidapi.com) para acessar a [Medium API](https://rapidapi.com/nishujain199719-vgIfuFHZxVZ/api/medium2)
- WordPress com REST API habilitada
- Application Password do WordPress (para autenticação)

## Instalação

### 1. Clone o repositório

```bash
git clone <seu-repositorio>
cd medium-blog-wordpress
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```env
# Medium API (RapidAPI)
RAPIDAPI_KEY=sua_chave_rapidapi
RAPIDAPI_HOST=medium2.p.rapidapi.com

# WordPress
WORDPRESS_URL=https://seu-site.com
WORDPRESS_USERNAME=seu_usuario
WORDPRESS_PASSWORD=sua_senha_aplicacao

# Configurações de busca
SEARCH_KEYWORDS=python,javascript,react,nodejs,AI
MAX_ARTICLES_PER_RUN=5
LANGUAGE_PREFERENCE=both

# Agendamento
SCHEDULE_HOUR=9
SCHEDULE_MINUTE=0
TIMEZONE=America/Sao_Paulo

# Preferências de conteúdo
POST_STATUS=draft
CATEGORY_ID=1
```

### 3. Inicie o container

```bash
docker-compose up -d
```

## Como obter as credenciais

### RapidAPI Key

1. Acesse [RapidAPI](https://rapidapi.com)
2. Crie uma conta gratuita
3. Busque por "Medium API" ou acesse diretamente [este link](https://rapidapi.com/nishujain199719-vgIfuFHZxVZ/api/medium2)
4. Clique em "Subscribe to Test"
5. Escolha o plano Basic (gratuito)
6. Copie sua `X-RapidAPI-Key` da seção "Code Snippets"

### WordPress Application Password

1. Acesse seu WordPress Admin
2. Vá para Usuários → Seu Perfil
3. Role até "Application Passwords"
4. Digite um nome (ex: "Medium Sync")
5. Clique em "Add New Application Password"
6. Copie a senha gerada (ela só aparece uma vez!)

## Uso

### Interface Web

Acesse `http://localhost:5000` para:

- Ver estatísticas de sincronização
- Executar sincronização manual
- Ver artigos recentes sincronizados
- Consultar logs de sincronização
- Verificar próximo agendamento

### API Endpoints

- `GET /` - Interface principal
- `POST /sync` - Executar sincronização manual
- `GET /api/status` - Status do sistema
- `GET /api/articles` - Listar artigos sincronizados
- `GET /api/logs` - Logs de sincronização
- `POST /test-connection` - Testar conexões com APIs

## Configuração de Palavras-chave

Edite `SEARCH_KEYWORDS` no `.env` para personalizar os tópicos:

```env
SEARCH_KEYWORDS=python,django,fastapi,machine learning,data science
```

Palavras-chave sugeridas por categoria:

- **Backend**: python,nodejs,java,golang,rust,api,microservices
- **Frontend**: react,vue,angular,javascript,typescript,css,html
- **DevOps**: docker,kubernetes,aws,azure,ci/cd,terraform
- **Data**: machine learning,data science,pandas,tensorflow,pytorch
- **Mobile**: react native,flutter,swift,kotlin,ios,android

## Configuração do WordPress

### Categorias

1. No WordPress, crie categorias para organizar os posts
2. Anote o ID da categoria desejada
3. Configure `CATEGORY_ID` no `.env`

### Status dos Posts

- `draft` - Salva como rascunho para revisão
- `publish` - Publica automaticamente

## Monitoramento

### Logs

Os logs são salvos em `logs/app.log`. Para visualizar em tempo real:

```bash
docker logs -f medium-wordpress-automation
```

### Banco de Dados

O histórico é salvo em SQLite em `data/medium_wordpress.db`.

## Troubleshooting

### Erro de conexão com WordPress

- Verifique se a REST API está habilitada
- Confirme URL do site (com ou sem www)
- Teste o Application Password

### Artigos não encontrados

- Verifique suas palavras-chave
- Confirme limite da API RapidAPI
- Teste manualmente na interface RapidAPI

### Container não inicia

```bash
# Ver logs
docker-compose logs

# Reconstruir imagem
docker-compose build --no-cache
docker-compose up -d
```

## Desenvolvimento

### Estrutura do projeto

```
medium-blog-wordpress/
├── src/
│   ├── config.py          # Configurações
│   ├── medium_api.py       # Cliente API Medium
│   ├── wordpress_api.py    # Cliente API WordPress
│   ├── database.py         # Modelos e persistência
│   ├── scheduler.py        # Agendamento de tarefas
│   ├── web_interface.py    # Interface Flask
│   └── main.py            # Entrada principal
├── templates/             # Templates HTML
├── static/               # Arquivos estáticos
├── data/                 # Banco de dados SQLite
└── logs/                 # Arquivos de log
```

### Executar localmente (sem Docker)

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar
python -m src.main
```

## Licença

MIT

## Suporte

Para problemas ou sugestões, abra uma issue no GitHub.