"""
Authentication module for Medium to WordPress application
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps

# Create auth blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize Flask-Login
login_manager = LoginManager()

class User(UserMixin):
    """Simple User class for Flask-Login"""
    def __init__(self, username):
        self.id = username
        self.username = username

    def get_id(self):
        return self.username

def init_auth(app):
    """Initialize authentication for the Flask app"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'
    
    # Secret key for sessions
    app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())
    
    # Register blueprint
    app.register_blueprint(auth_bp)

@login_manager.user_loader
def load_user(username):
    """Load user by username"""
    admin_user = os.getenv('ADMIN_USERNAME', 'admin')
    if username == admin_user:
        return User(username)
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Get credentials from environment
        admin_user = os.getenv('ADMIN_USERNAME', 'admin')
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        # Simple authentication check
        if username == admin_user and password == admin_pass:
            user = User(username)
            login_user(user, remember=True)
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('Você saiu do sistema com sucesso', 'success')
    return redirect(url_for('auth.login'))

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function