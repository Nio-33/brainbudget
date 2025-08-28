#!/usr/bin/env python3
"""
Start BrainBudget application on an available port.
"""
from app import create_app
import socket

def find_available_port():
    """Find an available port to run the application."""
    ports_to_try = [8080, 8000, 3000, 8888, 9000, 7000, 6000]
    
    for port in ports_to_try:
        try:
            # Test if port is available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result != 0:  # Port is available (connection failed)
                return port
        except Exception:
            continue
    
    return None

if __name__ == '__main__':
    print("🧠💰 Starting BrainBudget...")
    
    # Create Flask app
    app = create_app()
    
    # Find available port
    port = find_available_port()
    
    if port:
        print(f"✅ Found available port: {port}")
        print(f"🚀 Starting BrainBudget on port {port}...")
        print(f"")
        print(f"🌐 Access your application at:")
        print(f"📍 http://localhost:{port}")
        print(f"📍 http://127.0.0.1:{port}")
        print(f"")
        print(f"🎯 Landing Page: http://localhost:{port}/")
        print(f"🔐 Sign Up: http://localhost:{port}/auth/register")
        print(f"🏠 Dashboard: http://localhost:{port}/dashboard")
        print(f"")
        print(f"Ready to make budgeting ADHD-friendly! 🎉")
        print(f"")
        
        # Start the application
        app.run(
            host='127.0.0.1',
            port=port,
            debug=False,
            threaded=True
        )
    else:
        print("❌ No available ports found")
        print("💡 Try closing other applications and restart")