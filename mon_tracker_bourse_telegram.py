
import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json
import requests
import streamlit as st

# 🔒 Mot de passe à définir ici
CORRECT_PASSWORD = "million$tracker2024"

# Authentification simple
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    password = st.text_input("Mot de passe", type="password")
    if password == CORRECT_PASSWORD:
        st.session_state["authenticated"] = True
        st.experimental_rerun()
    else:
        st.stop()

# -------------------- CONFIGURATION -------------------- #
DEFAULT_WATCHLIST = ["HAG.DE", "RHM.DE", "HO.PA", "LDO.MI", "NVDA", "MSFT", "META", "AVGO"]
DATA_FILE = "user_data.json"

# Configuration Telegram (à personnaliser)
TELEGRAM_TOKEN = "VOTRE_TOKEN_TELEGRAM"
TELEGRAM_CHAT_ID = "VOTRE_CHAT_ID"

# -------------------- FONCTIONS -------------------- #
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"watchlist": DEFAULT_WATCHLIST, "portfolio": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def compute_signals(df):
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA50"] = df["Close"].rolling(window=50).mean()
    return df

def get_signal(rsi):
    if pd.isna(rsi):
        return "⚪ HOLD"
    elif rsi < 30:
        return "🟢 BUY"
    elif rsi > 70:
        return "🔴 SELL"
    else:
        return "⚪ HOLD"

def send_telegram_alert(ticker, signal, rsi):
    message = f"🔔 ALERTE BOURSE\n\nTicker : {ticker}\nSignal : {signal}\nRSI : {round(rsi, 2)}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            st.error(f"Erreur Telegram : {response.text}")
    except Exception as e:
        st.error(f"Exception Telegram : {e}")

# -------------------- INTERFACE -------------------- #
st.set_page_config(page_title="📊 Mon Tracker Bourse + Telegram", layout="wide")
st.title("📊 Suivi Boursier avec Alertes Telegram")

data = load_data()

# Sidebar : Ajout à la watchlist
with st.sidebar:
    st.header("🔍 Watchlist personnalisée")
    new_ticker = st.text_input("Ajouter un symbole (ex: AAPL, AIR.PA)")
    if st.button("Ajouter"):
        if new_ticker and new_ticker not in data["watchlist"]:
            data["watchlist"].append(new_ticker.upper())
            save_data(data)
            st.experimental_rerun()

    st.header("💼 Mon Portefeuille")
    ticker_input = st.selectbox("Choisir une action", data["watchlist"])
    qty = st.number_input("Quantité", min_value=0, step=1)
    price = st.number_input("Prix d'achat (€)", min_value=0.0, step=0.1)
    if st.button("Ajouter au portefeuille"):
        if qty > 0 and price > 0:
            data["portfolio"][ticker_input] = {"qty": qty, "price": price}
            save_data(data)
            st.success(f"{ticker_input} ajouté au portefeuille.")

# Corps principal : Affichage des données
for ticker in data["watchlist"]:
    st.subheader(f"📌 {ticker}")
    stock = yf.Ticker(ticker)
    df = stock.history(period="6mo")
    if df.empty:
        st.warning("Données indisponibles.")
        continue

    df = compute_signals(df)
    rsi_value = df["RSI"].iloc[-1]
    signal = get_signal(rsi_value)
    st.markdown(f"**Signal RSI actuel : {signal}**")

    # Graphiques
    st.line_chart(df[["Close", "MA20", "MA50"]])
    st.line_chart(df[["RSI"]])

    # Alerte Telegram
    if signal != "⚪ HOLD":
        send_telegram_alert(ticker, signal, rsi_value)

# Affichage portefeuille
st.markdown("---")
st.header("📘 Suivi de mon portefeuille")

if not data["portfolio"]:
    st.info("Aucune position enregistrée.")
else:
    port_data = []
    for ticker, info in data["portfolio"].items():
        live = yf.Ticker(ticker).history(period="1d")
        if not live.empty:
            current_price = live["Close"].iloc[-1]
            pnl = (current_price - info["price"]) * info["qty"]
            port_data.append({
                "Ticker": ticker,
                "Quantité": info["qty"],
                "Prix achat (€)": info["price"],
                "Prix actuel (€)": round(current_price, 2),
                "Gain/Perte (€)": round(pnl, 2)
            })
    df_port = pd.DataFrame(port_data)
    st.dataframe(df_port)
