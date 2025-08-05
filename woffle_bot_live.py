#!/usr/bin/env python3
""" WOFFLE live trading bot (v3) """

import os, json, time, base64, requests
from dotenv import load_dotenv
from solana.rpc.api import Client
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.rpc.types import TxOpts

# ---------- env ----------
load_dotenv()
RPC_URL      = os.getenv("RPC_URL")
PRIVATE_KEY  = os.getenv("PRIVATE_KEY")
TOKEN_MINT   = os.getenv("TOKEN_MINT")
QUOTE_MINT   = os.getenv("QUOTE_MINT")
BIRDEYE_KEY  = os.getenv("BIRDEYE_API_KEY")
SLIPPAGE     = float(os.getenv("SLIPPAGE", 1))      # 1 %
CAP_USDC     = float(os.getenv("TRADE_SIZE_USDC", 0.01))  # 0.01 USDC per buy

STATE_FILE = "state.json"

# ---------- RPC & wallet ----------
client = Client(RPC_URL)
wallet = Keypair.from_secret_key(bytes(json.loads(PRIVATE_KEY)))

# ---------- Jupiter helpers ----------
JUP_Q = "https://quote-api.jup.ag/v6/quote"
JUP_S = "https://quote-api.jup.ag/v6/swap"

def spl_balance(mint:str) -> int:
    tot = 0
    for acc in client.get_token_accounts_by_owner(wallet.public_key, { "mint": mint })["result"]["value"]:
        lamports = int(client.get_token_account_balance(acc["pubkey"])["result"]["value"]["amount"])
        tot += lamports
    return tot

def jup_swap(inp:str, out:str, raw_amt:int):
    quote = requests.get(
        JUP_Q,
        params={
            "inputMint": inp,
            "outputMint": out,
            "amount": raw_amt,
            "slippageBps": int(SLIPPAGE*100)
        },
        timeout=10
    ).json()
    swap_tx = requests.post(
        JUP_S,
        json={
            "quote": quote,
            "userPublicKey": str(wallet.public_key),
            "wrapAndUnwrapSol": True
        },
        timeout=10
    ).json()["swapTransaction"]
    txn = Transaction.deserialize(base64.b64decode(swap_tx))
    txn.sign(wallet)
    sig = client.send_transaction(txn, wallet, opts=TxOpts(preflight_commitment="confirmed"))["result"]
    print("🔄 Jupiter swap sent:", sig)

# ---------- Price feed ----------
def fetch_price() -> float | None:
    url = f"https://public-api.birdeye.so/defi/price?address={TOKEN_MINT}"
    hdr = {"accept":"application/json","x-chain":"solana","x-api-key":BIRDEYE_KEY}
    try:
        return float(requests.get(url, headers=hdr, timeout=10).json()["data"]["value"])
    except Exception as e:
        print("⚠️ price error:", e)
        return None

# ---------- state ----------
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"last_price": None, "last_trade": None}
    return json.load(open(STATE_FILE))

def save_state(st): json.dump(st, open(STATE_FILE,"w"))

# ---------- main loop ----------
state = load_state()
print("🚀 WOFFLE bot v3 running – polling every 30 s…")

while True:
    price = fetch_price()
    if price is None:
        time.sleep(30); continue

    lp, lt = state["last_price"], state["last_trade"]
    print(f"Price: ${price:,.8f}")

    if lp and lt:
        change = (price - lp) / lp
        print(f"Δ since last {lt}: {change:+.2%}")
        if lt == "buy" and change <= -0.10:
            wbal = spl_balance(TOKEN_MINT)
            if wbal: jup_swap(TOKEN_MINT, QUOTE_MINT, wbal)
            state.update(last_price=price, last_trade="sell"); save_state(state)
        elif lt == "sell" and change >= 0.10:
            ubal = spl_balance(QUOTE_MINT)
            cap_raw = int(CAP_USDC * 1_000_000)   # USDC 6‑dec
            amt = min(ubal, cap_raw)
            if amt: jup_swap(QUOTE_MINT, TOKEN_MINT, amt)
            state.update(last_price=price, last_trade="buy"); save_state(state)
    elif lp is None:
        # first run: buy with cap
        ubal = spl_balance(QUOTE_MINT)
        amt  = min(ubal, int(CAP_USDC * 1_000_000))
        if amt: jup_swap(QUOTE_MINT, TOKEN_MINT, amt)
        state.update(last_price=price, last_trade="buy"); save_state(state)

    time.sleep(30)
