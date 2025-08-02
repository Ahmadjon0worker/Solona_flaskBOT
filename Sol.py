from flask import Flask, render_template_string, request, jsonify
import threading
import time
import random

app = Flask(__name__)

# Statistik ma'lumotlar
data = {
    "total_found": 0,
    "total_usd": 0.0,
    "sol_found": 0,
    "sol_usd": 0.0,
    "is_running_multi": False,
    "is_running_solana": False
}

# HTML interfeys
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Wallet Hunter AI</title>
    <style>
        body { font-family: Arial; text-align: center; background: #1e1e2f; color: white; }
        button { padding: 10px 20px; margin: 10px; font-size: 16px; border-radius: 5px; }
        .stats { margin-top: 20px; font-size: 18px; }
    </style>
</head>
<body>
    <h1>🚀 Wallet Hunter AI Panel</h1>
    <button onclick="start('multi')">Start MultiCoins 🔥</button>
    <button onclick="start('solana')">Start Solana ☀️</button>
    <div class="stats" id="stats">
        <p>🔍 Topilgan walletlar: <span id="found">0</span></p>
        <p>💰 Jami qiymati (USD): $<span id="usd">0.00</span></p>
        <p>🌞 Solana topilgan: <span id="solfound">0</span></p>
        <p>💸 Solana qiymati (USD): $<span id="solusd">0.00</span></p>
    </div>
    <script>
        function start(type) {
            fetch('/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ type: type })
            });
        }

        setInterval(() => {
            fetch('/stats')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('found').innerText = data.total_found;
                    document.getElementById('usd').innerText = data.total_usd.toFixed(2);
                    document.getElementById('solfound').innerText = data.sol_found;
                    document.getElementById('solusd').innerText = data.sol_usd.toFixed(2);
                });
        }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/start', methods=['POST'])
def start():
    content = request.get_json()
    if content['type'] == 'multi' and not data['is_running_multi']:
        threading.Thread(target=run_multicoins).start()
        data['is_running_multi'] = True
    elif content['type'] == 'solana' and not data['is_running_solana']:
        threading.Thread(target=run_solana).start()
        data['is_running_solana'] = True
    return '', 204

@app.route('/stats')
def stats():
    return jsonify(data)

# ------ Simulyatsiya qilingan checker funksiyalar ------
def run_multicoins():
    while True:
        time.sleep(2)
        found = random.choice([0, 1])
        if found:
            usd = round(random.uniform(10, 1000), 2)
            data['total_found'] += 1
            data['total_usd'] += usd


def run_solana():
    while True:
        time.sleep(3)
        found = random.choice([0, 1])
        if found:
            usd = round(random.uniform(5, 500), 2)
            data['sol_found'] += 1
            data['sol_usd'] += usd

if __name__ == '__main__':
    app.run(debug=True)
