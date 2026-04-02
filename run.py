"""
Agrico Hub SSDP Backend - Entry Point
Production-ready Flask application
"""

import os
from app import create_app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Get port from environment (Render sets this) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Debug mode only for local development
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    # Run the app
    if debug_mode:
        # Local development: use Flask dev server
        app.run(debug=True, host='0.0.0.0', port=port)
    else:
        # Production: Flask app is run by gunicorn (see render.yaml)
        # This block is fallback for non-gunicorn environments
        app.run(debug=False, host='0.0.0.0', port=port)