#!/usr/bin/env python3
"""
BrainBudget Flask Application Entry Point.
ADHD-friendly budgeting app with AI-powered spending analysis.
"""
import os
import logging
import argparse
from dotenv import load_dotenv

from app import create_app

# Load environment variables from .env file
load_dotenv()

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run the BrainBudget Flask application.')
    parser.add_argument('--port', type=int, default=os.environ.get('PORT', 5000), help='Port to run the application on.')
    parser.add_argument('--host', type=str, default=os.environ.get('HOST', '0.0.0.0'), help='Host to bind to.')
    args = parser.parse_args()

    # Get configuration from environment
    debug_mode = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 'yes']
    
    # Configure logging for development
    if debug_mode:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(name)s %(levelname)s: %(message)s'
        )
        app.logger.info("Starting BrainBudget in debug mode")
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(name)s %(levelname)s: %(message)s'
        )
        app.logger.info("Starting BrainBudget in production mode")
    
    # Print startup information
    print(f"""
    🧠💰 BrainBudget Starting Up! 
    
    Environment: {'Development' if debug_mode else 'Production'}
    Host: {args.host}
    Port: {args.port}
    Debug: {debug_mode}
    
    🌐 Access your app at:
    📍 http://localhost:{args.port}
    📍 http://127.0.0.1:{args.port}
    
    📄 Pages available:
    🏠 Homepage: http://localhost:{args.port}/
    🤝 Community: http://localhost:{args.port}/community
    📊 Dashboard: http://localhost:{args.port}/dashboard
    
    Ready to make budgeting fun and ADHD-friendly! 🎉
    """)
    
    # Run the application
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=debug_mode,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 BrainBudget shutting down gracefully. Thanks for using us!")
    except Exception as e:
        print(f"❌ Error starting BrainBudget: {e}")
        app.logger.error(f"Application startup error: {e}")
        exit(1)
