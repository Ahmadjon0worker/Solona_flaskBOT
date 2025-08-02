import time
import requests
import base58
import nacl.signing
from flask import Flask
import threading

# Telegram sozlamalari
TOKEN = "8481417913:AAH65jDSXYt8Z9CKOJW2VwxVG-nuanTe-FE"
CHAT_ID = "7521446360"
SEND_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# Solana JSON RPC endpoint
RPC_URL = "https://api.mainnet-beta.solana.com"

# Flask ilova
app = Flask(__name__)

# Solana address generator
def generate_solana_address():
    signing_key = nacl.signing.SigningKey.generate()
    verify_key = signing_key.verify_key
    address = base58.b58encode(verify_key.encode()).decode()
    private = base58.b58encode(signing_key.encode() + verify_key.encode()).decode()
    return address, private

# Solana balansni tekshirish
def get_solana_balance(address):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address]
    }
    try:
        response = requests.post(RPC_URL, json=payload, timeout=10)
        data = response.json()
        return data.get("result", {}).get("value", 0)
    except:
        return 0

# Telegramga yuborish
def notify_telegram(address, privkey, balance):
    text = f"🔥 Topildi!\n📬 Address: `{address}`\n🔑 Private: `{privkey}`\n💰 Balance: {balance / 1_000_000_000} SOL"
    requests.post(SEND_URL, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

# Hunter funksiyasi (doimiy ishlaydi)
def wallet_hunter():
    while True:
        address, privkey = generate_solana_address()
        balance = get_solana_balance(address)
        print(f"[{time.strftime('%H:%M:%S')}] {address} | {balance} lamports")

        if balance > 0:
            notify_telegram(address, privkey, balance)
        time.sleep(0.3)

# Flask route
@app.route("/")
def home():
    return "Solana Hunter Flask App Ishlayapti!"

# Ishlashni boshlash
if __name__ == "__main__":
    t = threading.Thread(target=wallet_hunter)
    t.start()
    app.run(host="0.0.0.0", port=8080)
