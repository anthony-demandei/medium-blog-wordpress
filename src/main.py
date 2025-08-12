import logging
import sys
from .web_interface import WebInterface
from .config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application"""
    logger.info("Starting Medium to WordPress Automation...")
    
    # Validate configuration
    config_errors = Config.validate()
    if config_errors:
        logger.warning("Configuration issues detected:")
        for error in config_errors:
            logger.warning(f"  - {error}")
        logger.info("Application will start but some features may not work. Please check your .env file.")
    
    # Create and run web interface
    app = WebInterface()
    
    # Run Flask app
    is_debug = Config.FLASK_ENV == 'development'
    logger.info(f"Starting Flask application (debug={is_debug})...")
    
    try:
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=is_debug
        )
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()