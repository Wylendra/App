import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import json
import os
import io
from datetime import datetime, timedelta

# --- CONFIGURATION (Identique à votre code) ---
BENCHMARK_TICKER = "CW8.PA" 
CATALOGUE_ACHAT = {
    "MSCI World (CW8)": "CW8.PA", "S&P 500": "^GSPC", "CAC 40": "^FCHI", "Nasdaq 100": "^IXIC",
    "Airbus": "AIR.PA", "LVMH": "MC.PA", "Michelin": "ML.PA", "TotalEnergies": "TTE.PA", 
    "Hermès": "RMS.PA", "L'Oréal": "OR.PA", "Sanofi": "SAN.PA", "AXA": "CS.PA",
    "Apple": "AAPL", "Microsoft": "MSFT", "Nvidia": "NVDA", "Tesla": "TSLA", 
    "Bitcoin": "BTC-EUR", "Ethereum": "ETH-EUR"
}
ICONES = {
    "AAPL": "🍎", "MSFT": "💻", "TSLA": "⚡", "NVDA": "🎮", "MC.PA": "👜", 
    "AIR.PA": "✈️", "TTE.PA": "⛽", "ML.PA": "🛞", "BTC-EUR": "₿", "ETH-EUR": "Ξ",
    "CW8.PA": "🌍", "^FCHI": "🇫🇷"
}
SAVE_FILE = "data_bourse.json"

# --- LOGIQUE DE DONNÉES ---
def charger_donnees():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            d = json.load(f)
            return d.get("portefeuille", {}), d.get("ventes", [])
    return {}, []

def sauvegarder_donnees(portefeuille, ventes):
    with open(SAVE_FILE, "w") as f:
        json.dump({"portefeuille": portefeuille, "ventes": ventes}, f)

# --- INITIALISATION ---
if 'portefeuille' not in st.session_state:
    st.session_state.portefeuille, st.session_state.ventes = charger_donnees()

st.set_page_config(page_title="Portfolio Tracker Pro", layout="wide")

# --- INTERFACE ---
st.title("📊 Portfolio Tracker Pro v2.0")

tabs = st.tabs(["📊 Analyse", "💼 Positions", "💸 Ventes", "📈 Benchmark"])

# --- ONGLET ANALYSE (Dashboard / Ajout) ---
with tabs[0]:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("NOUVEL ACHAT")
        t_nom = st.selectbox("Ticker:", list(CATALOGUE_ACHAT.keys()))
        t_code = CATALOGUE_ACHAT[t_nom]
        p = st.number_input("PRU Achat (€):", min_value=0.0, format="%.2f")
        q = st.number_input("Quantité:", min_value=0.0, format="%.2f")
        d = st.date_input("Date:", datetime.now())
        
        if st.button("AJOUTER"):
            t = t_code.upper()
            if t in st.session_state.portefeuille:
                qa, pa = st.session_state.portefeuille[t]['qty'], st.session_state.portefeuille[t]['pru']
                qt = qa + q
                st.session_state.portefeuille[t]['pru'] = ((qa * pa) + (q * p)) / qt
                st.session_state.portefeuille[t]['qty'] = qt
            else:
                st.session_state.portefeuille[t] = {'pru': p, 'qty': q, 'date': str(d)}
            sauvegarder_donnees(st.session_state.portefeuille, st.session_state.ventes)
            st.rerun()

# --- ONGLET POSITIONS (Liste) ---
with tabs[1]:
    st.subheader("Positions Actuelles")
    data_list = []
    lat_totale, investi_total = 0, 0
    
    for t, i in st.session_state.portefeuille.items():
        try:
            p_live = yf.Ticker(t).fast_info['last_price']
            val_actuelle, val_achat = p_live * i['qty'], i['pru'] * i['qty']
            pf = val_actuelle - val_achat
            lat_totale += pf; investi_total += val_achat
            
            data_list.append({
                "Icon": ICONES.get(t, "📈"), "Ticker": t, "Prix Live": f"{p_live:.2f}€",
                "PRU": f"{i['pru']:.2f}€", "Qté": i['qty'], "Valeur": f"{val_actuelle:.2f}€",
                "Perf %": f"{(p_live/i['pru']-1)*100:+.2f}%", "Perf €": f"{pf:+.2f}€"
            })
        except: continue
    
    if data_list:
        st.table(pd.DataFrame(data_list))
        lat_perc = (lat_totale / investi_total * 100) if investi_total > 0 else 0
        st.metric("Plus-Value Latente", f"{lat_totale:+.2f} €", f"{lat_perc:+.2f}%")

# --- ONGLET VENTES ---
with tabs[2]:
    st.subheader("ENREGISTRER UNE VENTE")
    v_t = st.selectbox("Action à vendre", list(st.session_state.portefeuille.keys()))
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1: pv = st.number_input("Prix Vente (€)", min_value=0.0)
    with col_v2: qv = st.number_input("Qté à vendre", min_value=0.0)
    with col_v3: dv = st.date_input("Date Vente", datetime.now())
    
    if st.button("VENDRE"):
        if v_t in st.session_state.portefeuille and qv <= st.session_state.portefeuille[v_t]['qty']:
            pa_v = st.session_state.portefeuille[v_t]['pru']
            st.session_state.ventes.append({'ticker': v_t, 'gain': (pv - pa_v) * qv, 'date': str(dv), 'pru_achat': pa_v, 'qty_vendu': qv})
            st.session_state.portefeuille[v_t]['qty'] -= qv
            if st.session_state.portefeuille[v_t]['qty'] <= 0: del st.session_state.portefeuille[v_t]
            sauvegarder_donnees(st.session_state.portefeuille, st.session_state.ventes)
            st.rerun()

    st.write("Historique des Ventes")
    st.dataframe(pd.DataFrame(st.session_state.ventes))

# --- ONGLET BENCHMARK ---
with tabs[3]:
    if st.button("ACTUALISER BENCHMARK"):
        try:
            plt.style.use('dark_background')
            debut_annee = "2026-01-01"
            bench_df = yf.download(BENCHMARK_TICKER, start=debut_annee)
            bench_close = bench_df['Close'].squeeze()
            perc_w = ((bench_close / bench_close.iloc[0]) - 1) * 100
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(perc_w, color="#f7768e", label="MSCI World")
            ax.set_title("Comparaison YTD")
            ax.legend()
            st.pyplot(fig)
        except: st.error("Erreur de chargement des données de benchmark.")
