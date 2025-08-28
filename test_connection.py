#!/usr/bin/env python3
"""
Test connection and create a working HTTP server for BrainBudget.
"""
import http.server
import socketserver
import webbrowser
import os
from threading import Timer

# Create the BrainBudget HTML content
html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BrainBudget - ADHD-Friendly Financial Management</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #EFDFC5; }
        .brain-gradient { background: linear-gradient(135deg, #380F17 0%, #8F0B13 100%); }
    </style>
</head>
<body class="min-h-screen">
    <!-- Header -->
    <header class="absolute top-4 left-4 right-4 z-10">
        <div class="flex justify-between items-center">
            <div class="flex items-center space-x-2">
                <span class="text-3xl">🧠</span>
                <span class="text-xl font-bold" style="color: #380F17;">BrainBudget</span>
            </div>
            <button class="px-4 py-2 rounded-full text-sm font-medium text-white brain-gradient">
                Get Started
            </button>
        </div>
    </header>

    <!-- Main Content -->
    <main class="flex items-center justify-center min-h-screen px-4">
        <div class="text-center max-w-4xl mx-auto">
            <!-- Hero Section -->
            <div class="mb-16">
                <div class="mb-8">
                    <span class="text-8xl">🧠💰</span>
                </div>
                <h1 class="text-6xl md:text-7xl font-bold mb-6" style="color: #380F17;">
                    BrainBudget
                </h1>
                <p class="text-xl md:text-2xl mb-8" style="color: #252B2B;">
                    The first budgeting app designed specifically for ADHD brains
                </p>
                <p class="text-lg max-w-2xl mx-auto mb-12" style="color: #4C4F54;">
                    Transform your financial chaos into clarity with AI-powered insights, gentle guidance, 
                    and neurodivergent-friendly design that actually works with your brain.
                </p>
                
                <button class="px-12 py-4 rounded-full font-bold text-xl text-white brain-gradient hover:shadow-xl transition-all duration-300 mb-4"
                        onclick="showMessage()">
                    🚀 Get Started Free
                </button>
                
                <p class="text-sm" style="color: #4C4F54;">
                    No credit card required • ADHD-friendly onboarding
                </p>
            </div>
            
            <!-- Feature Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="bg-white bg-opacity-70 rounded-3xl p-6 text-center hover:shadow-lg transition-all">
                    <div class="text-4xl mb-4">🤖</div>
                    <h3 class="text-lg font-semibold mb-2" style="color: #380F17;">AI-Powered Analysis</h3>
                    <p class="text-sm" style="color: #4C4F54;">
                        Upload your bank statement and get instant, non-judgmental insights about your spending patterns.
                    </p>
                </div>
                
                <div class="bg-white bg-opacity-70 rounded-3xl p-6 text-center hover:shadow-lg transition-all">
                    <div class="text-4xl mb-4">🧠</div>
                    <h3 class="text-lg font-semibold mb-2" style="color: #380F17;">Built for ADHD</h3>
                    <p class="text-sm" style="color: #4C4F54;">
                        Every feature designed with executive function challenges in mind. No overwhelming spreadsheets.
                    </p>
                </div>
                
                <div class="bg-white bg-opacity-70 rounded-3xl p-6 text-center hover:shadow-lg transition-all">
                    <div class="text-4xl mb-4">🤝</div>
                    <h3 class="text-lg font-semibold mb-2" style="color: #380F17;">Supportive Community</h3>
                    <p class="text-sm" style="color: #4C4F54;">
                        Connect with other ADHD individuals on similar financial journeys. Share wins, get support.
                    </p>
                </div>
            </div>
        </div>
    </main>

    <!-- Success Message -->
    <div id="successMessage" class="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg hidden">
        🎉 BrainBudget Landing Page is working perfectly! Full Flask app coming soon.
    </div>

    <script>
        function showMessage() {
            document.getElementById('successMessage').classList.remove('hidden');
            setTimeout(() => {
                document.getElementById('successMessage').classList.add('hidden');
            }, 4000);
        }
        
        // Add smooth animations
        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.grid > div');
            cards.forEach((card, index) => {
                setTimeout(() => {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(20px)';
                    card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0)';
                    }, 100);
                }, index * 200);
            });
        });
    </script>
</body>
</html>"""

# Write the HTML file
with open('/Users/nio/BrainBudget/brainbudget_working.html', 'w') as f:
    f.write(html_content)

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        else:
            super().do_GET()

def open_browser():
    webbrowser.open('http://localhost:8000')

if __name__ == '__main__':
    PORT = 8000
    
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print("🧠💰 BrainBudget HTTP Server Starting...")
            print(f"✅ Server running on http://localhost:{PORT}")
            print(f"📍 Also available at http://127.0.0.1:{PORT}")
            print(f"🎯 Landing Page: http://localhost:{PORT}/")
            print(f"")
            print(f"🎉 BrainBudget is ready! Opening browser...")
            
            # Auto-open browser after 2 seconds
            Timer(2.0, open_browser).start()
            
            httpd.serve_forever()
            
    except OSError as e:
        print(f"❌ Could not start server on port {PORT}: {e}")
        print("💡 Try a different port or check if something else is using port 8000")
    except KeyboardInterrupt:
        print(f"\n👋 BrainBudget server stopped gracefully!")