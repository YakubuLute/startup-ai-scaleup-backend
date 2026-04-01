import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Render sets PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    
    # Debug mode only for local development
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    if debug:
        app.run(debug=True, host='0.0.0.0', port=port)
    else:
        # For production (Render uses gunicorn, but this is fallback)
        app.run(host='0.0.0.0', port=port)