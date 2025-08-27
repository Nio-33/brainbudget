#!/usr/bin/env python3
"""
Production WSGI Server for BrainBudget
Uses Gunicorn for better performance and reliability.
"""
import os
import sys
import socket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def find_available_port(start=8000):
    """Find an available port starting from the given port."""
    for port in range(start, start + 10):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    return None

def main():
    """Run BrainBudget with Gunicorn production server."""
    print("🧠💰 BrainBudget Production Server")
    print("=" * 40)
    
    # Find available port
    port = find_available_port(8000)
    if not port:
        print("❌ No available ports found")
        return
    
    # Gunicorn configuration
    workers = 2
    timeout = 120
    bind_address = f"0.0.0.0:{port}"
    
    # Create gunicorn command
    cmd = [
        'gunicorn',
        '--workers', str(workers),
        '--timeout', str(timeout),
        '--bind', bind_address,
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--log-level', 'info',
        'app:create_app()'
    ]
    
    print(f"🚀 Starting production server...")
    print(f"📍 URL: http://localhost:{port}")
    print(f"📍 URL: http://127.0.0.1:{port}")
    print(f"⚙️  Workers: {workers}")
    print(f"⏱️  Timeout: {timeout}s")
    print(f"\n🔥 Starting Gunicorn server...")
    
    try:
        os.execvp('gunicorn', cmd)
    except FileNotFoundError:
        print("❌ Gunicorn not found. Installing...")
        import subprocess
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'gunicorn'])
        os.execvp('gunicorn', cmd)
    except Exception as e:
        print(f"❌ Error starting production server: {e}")
        print("\n🔄 Falling back to development server...")
        
        # Fallback to Flask development server
        from app import create_app
        app = create_app('development')
        app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()