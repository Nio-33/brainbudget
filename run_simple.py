#!/usr/bin/env python3
"""
Simple Flask server for BrainBudget to bypass port issues.
"""
from flask import Flask, render_template
import os

# Create a minimal Flask app
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')

app.config['SECRET_KEY'] = 'dev-key-for-testing'

@app.route('/')
def landing_page():
    """Serve the landing page."""
    try:
        return render_template('landing.html')
    except Exception as e:
        return f"""
        <h1>🧠💰 BrainBudget</h1>
        <p>Template error: {e}</p>
        <p><a href="/simple">Try Simple Version</a></p>
        """

@app.route('/simple')
def simple_page():
    """Simple version of the landing page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BrainBudget - ADHD-Friendly Budgeting</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background-color: #EFDFC5; }
        </style>
    </head>
    <body class="min-h-screen flex items-center justify-center">
        <div class="text-center max-w-4xl mx-auto p-8">
            <div class="mb-8">
                <span class="text-8xl">🧠💰</span>
            </div>
            <h1 class="text-6xl font-bold mb-6" style="color: #380F17;">
                BrainBudget
            </h1>
            <p class="text-xl mb-8" style="color: #252B2B;">
                The first budgeting app designed specifically for ADHD brains
            </p>
            <p class="text-lg max-w-2xl mx-auto mb-12" style="color: #4C4F54;">
                Transform your financial chaos into clarity with AI-powered insights, 
                gentle guidance, and neurodivergent-friendly design that actually works with your brain.
            </p>
            
            <div class="space-y-4">
                <button class="px-12 py-4 rounded-full font-bold text-xl text-white" 
                        style="background-color: #380F17;"
                        onclick="alert('🎉 BrainBudget is working! Full app needs proper Flask server.')">
                    🚀 Get Started Free
                </button>
                
                <p class="text-sm" style="color: #4C4F54;">
                    No credit card required • ADHD-friendly onboarding
                </p>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
                <div class="bg-white bg-opacity-70 rounded-3xl p-6 text-center">
                    <div class="text-4xl mb-4">🤖</div>
                    <h3 class="text-lg font-semibold mb-2" style="color: #380F17;">AI-Powered Analysis</h3>
                    <p class="text-sm" style="color: #4C4F54;">Upload your bank statement and get instant, non-judgmental insights.</p>
                </div>
                
                <div class="bg-white bg-opacity-70 rounded-3xl p-6 text-center">
                    <div class="text-4xl mb-4">🧠</div>
                    <h3 class="text-lg font-semibold mb-2" style="color: #380F17;">Built for ADHD</h3>
                    <p class="text-sm" style="color: #4C4F54;">Every feature designed with executive function challenges in mind.</p>
                </div>
                
                <div class="bg-white bg-opacity-70 rounded-3xl p-6 text-center">
                    <div class="text-4xl mb-4">🤝</div>
                    <h3 class="text-lg font-semibold mb-2" style="color: #380F17;">Supportive Community</h3>
                    <p class="text-sm" style="color: #4C4F54;">Connect with other ADHD individuals on similar financial journeys.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("🧠💰 Starting Simple BrainBudget Server...")
    print("📍 Access at: http://localhost:8080")
    print("📍 Alternative: http://127.0.0.1:8080")
    print("🎯 Landing Page: http://localhost:8080/")
    print("🔧 Simple Version: http://localhost:8080/simple")
    print("")
    
    try:
        app.run(
            host='0.0.0.0',
            port=8080,
            debug=False
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("💡 Try a different port or check firewall settings")