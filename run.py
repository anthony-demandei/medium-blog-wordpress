#!/usr/bin/env python3
"""Main entry point for the Medium to WordPress sync application"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from web_interface import WebInterface
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

# Create Flask app instance for gunicorn
def create_app():
    """Create and configure the Flask application"""
    web_interface = WebInterface()
    return web_interface.app

# For production with gunicorn
app = create_app()

# For development/direct execution
if __name__ == '__main__':
    is_debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=5001, debug=is_debug)