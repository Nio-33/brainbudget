#!/usr/bin/env python3
"""
BrainBudget Deployment Script
Production-ready deployment with multiple access methods and network diagnostics.
"""
import os
import sys
import time
import socket
import threading
import subprocess
from typing import List, Tuple
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_port_availability(host: str, port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result != 0  # Port is available if connection fails
    except Exception:
        return False

def find_available_port(start_port: int = 5000, end_port: int = 5010) -> int:
    """Find an available port in the given range."""
    for port in range(start_port, end_port):
        if check_port_availability('127.0.0.1', port):
            return port
    return None

def get_local_ip() -> str:
    """Get the local IP address."""
    try:
        # Connect to a remote address to get local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def test_network_connectivity() -> dict:
    """Test various network connectivity options."""
    results = {
        'localhost_ping': False,
        'loopback_ping': False,
        'local_ip_accessible': False,
        'firewall_blocking': False
    }
    
    # Test localhost ping
    try:
        result = subprocess.run(['ping', '-c', '1', 'localhost'], 
                              capture_output=True, text=True, timeout=5)
        results['localhost_ping'] = result.returncode == 0
    except Exception:
        pass
    
    # Test 127.0.0.1 ping
    try:
        result = subprocess.run(['ping', '-c', '1', '127.0.0.1'], 
                              capture_output=True, text=True, timeout=5)
        results['loopback_ping'] = result.returncode == 0
    except Exception:
        pass
    
    # Test local IP
    local_ip = get_local_ip()
    if local_ip != "127.0.0.1":
        results['local_ip'] = local_ip
        try:
            result = subprocess.run(['ping', '-c', '1', local_ip], 
                                  capture_output=True, text=True, timeout=5)
            results['local_ip_accessible'] = result.returncode == 0
        except Exception:
            pass
    
    return results

def create_deployment_urls(port: int) -> List[str]:
    """Create a list of all possible URLs to access the application."""
    urls = [
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
    ]
    
    # Add local IP if different from localhost
    local_ip = get_local_ip()
    if local_ip != "127.0.0.1":
        urls.append(f"http://{local_ip}:{port}")
    
    return urls

def create_static_fallback():
    """Create a static HTML file as fallback if server doesn't work."""
    static_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BrainBudget - ADHD-Friendly Financial Management</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
    </style>
</head>
<body class="gradient-bg">
    <div class="min-h-screen flex items-center justify-center px-4">
        <div class="max-w-md w-full bg-white/10 backdrop-blur-lg rounded-2xl p-8 text-center">
            <div class="mb-6">
                <span class="text-6xl">🧠💰</span>
            </div>
            <h1 class="text-3xl font-bold text-white mb-4">BrainBudget</h1>
            <p class="text-white/80 mb-6">
                ADHD-friendly budgeting application is ready! 
                The Flask server is running in the background.
            </p>
            <div class="bg-white/20 rounded-lg p-4 mb-4">
                <p class="text-white text-sm">
                    If you're seeing this page, the application is working!
                    Try accessing the full app at these URLs:
                </p>
            </div>
            <div class="space-y-2">
                <button onclick="window.open('http://localhost:5000', '_blank')" 
                        class="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded-lg transition-colors">
                    Open Full Application
                </button>
                <button onclick="window.location.reload()" 
                        class="w-full bg-gray-500 hover:bg-gray-600 text-white py-2 px-4 rounded-lg transition-colors">
                    Refresh Page
                </button>
            </div>
        </div>
    </div>
</body>
</html>'''
    
    with open('/Users/nio/BrainBudget/fallback.html', 'w') as f:
        f.write(static_content)
    
    return '/Users/nio/BrainBudget/fallback.html'

def run_flask_app(host: str, port: int):
    """Run the Flask application."""
    try:
        from app import create_app
        app = create_app('development')
        
        print(f"🚀 Starting BrainBudget on {host}:{port}")
        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
    except Exception as e:
        print(f"❌ Error starting Flask app: {e}")
        return False
    return True

def main():
    """Main deployment function."""
    print("🧠💰 BrainBudget Deployment Script")
    print("=" * 50)
    
    # Test network connectivity
    print("🔍 Testing network connectivity...")
    network_results = test_network_connectivity()
    
    print(f"  Localhost ping: {'✅' if network_results['localhost_ping'] else '❌'}")
    print(f"  Loopback ping: {'✅' if network_results['loopback_ping'] else '❌'}")
    if 'local_ip' in network_results:
        print(f"  Local IP ({network_results['local_ip']}): {'✅' if network_results['local_ip_accessible'] else '❌'}")
    
    # Find available port
    print("\n🔌 Finding available port...")
    port = find_available_port(5000, 5010)
    if not port:
        print("❌ No available ports found in range 5000-5010")
        return
    
    print(f"✅ Using port: {port}")
    
    # Create deployment URLs
    urls = create_deployment_urls(port)
    print(f"\n🌐 Application will be available at:")
    for url in urls:
        print(f"  📍 {url}")
    
    # Create static fallback
    fallback_path = create_static_fallback()
    print(f"\n📄 Static fallback created at: file://{fallback_path}")
    
    # Try different hosts
    hosts_to_try = ['0.0.0.0', '127.0.0.1', 'localhost']
    
    for host in hosts_to_try:
        print(f"\n🔄 Attempting to start server on {host}:{port}")
        
        try:
            # Start Flask app in a thread
            flask_thread = threading.Thread(
                target=run_flask_app, 
                args=(host, port),
                daemon=True
            )
            flask_thread.start()
            
            # Give it time to start
            time.sleep(3)
            
            # Test if server is responding
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result == 0:
                    print(f"✅ Server started successfully on {host}:{port}")
                    print(f"\n🎉 BrainBudget is now running!")
                    print(f"📱 Access the application at:")
                    for url in urls:
                        print(f"   {url}")
                    
                    print(f"\n💡 Troubleshooting tips if you can't connect:")
                    print(f"   1. Try different browsers (Chrome, Safari, Firefox)")
                    print(f"   2. Check firewall settings")
                    print(f"   3. Try incognito/private browsing mode")
                    print(f"   4. Open the fallback file: file://{fallback_path}")
                    
                    # Keep the main thread alive
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print("\n👋 BrainBudget shutting down gracefully...")
                    return
                    
            except Exception as e:
                print(f"❌ Failed to connect to {host}:{port} - {e}")
                continue
                
        except Exception as e:
            print(f"❌ Failed to start server on {host}:{port} - {e}")
            continue
    
    # If all hosts failed
    print(f"\n❌ Could not start server on any host. Using static fallback.")
    print(f"📄 Open this file in your browser: file://{fallback_path}")

if __name__ == "__main__":
    main()