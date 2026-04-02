"""
Agrico Hub SSDP Backend - Entry Point
Production-ready Flask application for Render
"""

import os
from app import create_app

# Create the Flask application instance
# Gunicorn will import this as: run:app
app = create_app()

# This block only runs when executed directly (local dev)
# Gunicorn imports the 'app' variable above and runs it separately
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)