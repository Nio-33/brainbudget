#!/bin/bash
# BrainBudget Network Diagnostics and Fix Script

echo "🔍 BrainBudget Network Diagnostics"
echo "=================================="

# Check if script is run with sudo
if [[ $EUID -ne 0 ]]; then
   echo "⚠️  This script needs admin privileges for network fixes."
   echo "   Run with: sudo ./fix_network.sh"
   echo ""
fi

# 1. Check hosts file
echo "📋 1. Checking /etc/hosts file..."
if grep -q "127.0.0.1.*localhost" /etc/hosts; then
    echo "✅ localhost entry exists in /etc/hosts"
else
    echo "❌ Missing localhost entry in /etc/hosts"
    if [[ $EUID -eq 0 ]]; then
        echo "127.0.0.1    localhost" >> /etc/hosts
        echo "✅ Added localhost entry to /etc/hosts"
    fi
fi

# 2. Check firewall status
echo ""
echo "🔥 2. Checking macOS Firewall..."
firewall_status=$(sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate)
echo "   Firewall status: $firewall_status"

# 3. Test network connectivity
echo ""
echo "🌐 3. Testing network connectivity..."
if ping -c 1 127.0.0.1 >/dev/null 2>&1; then
    echo "✅ Loopback (127.0.0.1) is reachable"
else
    echo "❌ Loopback (127.0.0.1) is NOT reachable - MAJOR ISSUE"
fi

if ping -c 1 localhost >/dev/null 2>&1; then
    echo "✅ localhost is reachable"
else
    echo "❌ localhost is NOT reachable"
fi

# 4. Check for processes using common ports
echo ""
echo "🔌 4. Checking ports 5000-5010..."
for port in {5000..5010}; do
    if lsof -i:$port >/dev/null 2>&1; then
        process=$(lsof -i:$port | tail -n1 | awk '{print $1, $2}')
        echo "   Port $port: BUSY ($process)"
    else
        echo "   Port $port: AVAILABLE"
    fi
done

# 5. Check network interfaces
echo ""
echo "🔧 5. Network interface status..."
ifconfig lo0 | grep "inet " | head -1

# 6. DNS resolution test
echo ""
echo "📡 6. DNS resolution test..."
if nslookup localhost >/dev/null 2>&1; then
    echo "✅ DNS resolution working"
else
    echo "❌ DNS resolution issues"
fi

# 7. Suggest fixes
echo ""
echo "🛠️  RECOMMENDED FIXES:"
echo "======================"
echo ""
echo "1. DISABLE FIREWALL TEMPORARILY:"
echo "   System Preferences → Security & Privacy → Firewall → Turn Off"
echo ""
echo "2. FLUSH DNS CACHE:"
echo "   sudo dscacheutil -flushcache"
echo ""
echo "3. RESET NETWORK INTERFACES:"
echo "   sudo ifconfig lo0 down && sudo ifconfig lo0 up"
echo ""
echo "4. CHECK FOR VPN/PROXY:"
echo "   System Preferences → Network → Check for VPN or Proxy settings"
echo ""
echo "5. RESTART NETWORK SERVICES:"
echo "   sudo launchctl unload /System/Library/LaunchDaemons/com.apple.networking.discovery.plist"
echo "   sudo launchctl load /System/Library/LaunchDaemons/com.apple.networking.discovery.plist"
echo ""

# Auto-fix attempts (if run as root)
if [[ $EUID -eq 0 ]]; then
    echo "🔧 ATTEMPTING AUTO-FIXES..."
    echo ""
    
    echo "   Flushing DNS cache..."
    dscacheutil -flushcache
    
    echo "   Resetting loopback interface..."
    ifconfig lo0 down
    sleep 1
    ifconfig lo0 up
    
    echo "   ✅ Auto-fixes applied"
    echo ""
    echo "   Please test localhost connection now!"
fi

echo "💡 ALTERNATIVE: Use the standalone app - it works without localhost!"
echo "   Open: file:///Users/nio/BrainBudget/standalone_app.html"