#!/bin/bash

echo "🔧 BrainBudget macOS Network Fix"
echo "================================"
echo ""

echo "1. Checking macOS Firewall status..."
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

echo ""
echo "2. Checking if Python is allowed through firewall..."
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep -i python

echo ""
echo "3. Attempting to add Python to firewall exceptions..."
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3

echo ""
echo "4. Checking available network interfaces..."
ifconfig | grep -E "inet 127|inet 192|inet 10"

echo ""
echo "5. Testing port availability..."
for port in 8080 8000 3000 9000; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "❌ Port $port is in use"
    else
        echo "✅ Port $port is available"
    fi
done

echo ""
echo "6. Recommended fixes:"
echo "   • Go to System Preferences → Security & Privacy → Firewall"
echo "   • Add Python to firewall exceptions"
echo "   • Temporarily disable VPN if connected"
echo "   • Try running: sudo dscacheutil -flushcache"
echo ""
echo "🎯 Alternative: Open the HTML file directly (no server needed)"
echo "   File location: /Users/nio/BrainBudget/brainbudget_standalone_final.html"