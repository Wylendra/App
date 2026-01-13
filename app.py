import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION & CONSTANTES ---
BENCHMARK_TICKER = "CW8.PA"
SAVE_FILE = "data_bourse.json"

CATALOGUE_ACHAT = {
    "MSCI World (CW8)": "CW8.PA", "S&P 500": "^GSPC", "CAC 40": "^FCHI", "Nasdaq 100": "^IXIC",
    "Airbus": "AIR.PA", "LVMH": "MC.PA", "Michelin": "ML.PA", "TotalEnergies": "TTE.PA", 
    "Hermès": "RMS.PA", "L'Oréal": "OR.PA", "Sanofi": "SAN.PA", "AXA": "CS.PA",
    "Apple": "AAPL", "Microsoft": "MSFT", "Nvidia": "NVDA", "Tesla": "TSLA", 
    "Bitcoin": "BTC-EUR", "Ethereum": "ETH-EUR"
}

# --- FONCTIONS DE LOGIQUE (Inchangées sur le fond) ---

def charger_donnees():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            d = json.load(f)
            return d.get("portefeuille", {}), d.get("ventes", [])
    return {}, []

def sauvegarder_donnees(portefeuille, ventes):
    with open(SAVE_FILE, "w") as f:
        json.dump({"portefeuille": portefeuille, "ventes": ventes}, f)

# --- INTERFACE STREAMLIT ---

st.set_page_config(page_title="Portfolio Tracker Pro", layout="wide")

# Initialisation des données dans la session Streamlit
if 'portefeuille' not in st.session_state:
    st.session_state.portefeuille, st.session_state.ventes = charger_donnees()

st.title("💼 Portfolio Tracker Pro v2.0 (Web Edition)")

# Sidebar pour l'ajout d'actifs
with st.sidebar:
    st.header("➕ Nouvel Achat")
    ticker_nom = st.selectbox("Sélectionner un actif", list(CATALOGUE_ACHAT.keys()))
    ticker_code = CATALOGUE_ACHAT[ticker_nom]
    pru = st.number_input("PRU Achat (€)", min_value=0.0, step=0.1)
    qty = st.number_input("Quantité", min_value=0.0, step=0.1)
    date_achat = st.date_input("Date d'achat", datetime.now())

    if st.button("Ajouter au Portefeuille"):
        t = ticker_code.upper()
        if t in st.session_state.portefeuille:
            qa, pa = st.session_state.portefeuille[t]['qty'], st.session_state.portefeuille[t]['pru']
            qt = qa + qty
            st.session_state.portefeuille[t]['pru'] = ((qa * pa) + (qty * pru)) / qt
            st.session_state.portefeuille[t]['qty'] = qt
        else:
            st.session_state.portefeuille[t] = {'pru': pru, 'qty': qty, 'date': str(date_achat)}
        sauvegarder_donnees(st.session_state.portefeuille, st.session_state.ventes)
        st.success(f"Ajouté : {t}")
        st.rerun()

# --- ONGLETS PRINCIPAUX ---
tab_pos, tab_ana, tab_ventes = st.tabs(["💼 Positions", "📊 Analyse & Benchmark", "💸 Ventes"])

with tab_pos:
    if not st.session_state.portefeuille:
        st.info("Votre portefeuille est vide.")
    else:
        st.subheader("État de vos positions")
        data_rows = []
        for t, i in st.session_state.portefeuille.items():
            try:
                price = yf.Ticker(t).fast_info['last_price']
                val_actuelle = price * i['qty']
                val_achat = i['pru'] * i['qty']
                perf_euro = val_actuelle - val_achat
                perf_perc = (price / i['pru'] - 1) * 100
                
                data_rows.append({
                    "Ticker": t,
                    "Prix Live": f"{price:.2f} €",
                    "PRU": f"{i['pru']:.2f} €",
                    "Qté": i['qty'],
                    "Valeur": f"{val_actuelle:.2f} €",
                    "Perf %": f"{perf_perc:+.2f}%",
                    "Perf €": f"{perf_euro:+.2f} €"
                })
            except: continue
        
        st.table(pd.DataFrame(data_rows))

with tab_ana:
    if st.session_state.portefeuille:
        st.subheader("Comparaison vs MSCI World (YTD)")
        # Ici on réutilise votre logique matplotlib
        try:
            debut_annee = "2026-01-01"
            bench_df = yf.download(BENCHMARK_TICKER, start=debut_annee)
            bench_close = bench_df['Close'].squeeze()
            perc_w = ((bench_close / bench_close.iloc[0]) - 1) * 100
            
            fig, ax = plt.subplots()
            ax.plot(perc_w, label="MSCI World", color="#f7768e")
            ax.set_title("Performance YTD")
            ax.legend()
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Erreur lors du traçage : {e}")

with tab_ventes:
    st.subheader("Historique des gains réalisés")
    if st.session_state.ventes:
        st.write(pd.DataFrame(st.session_state.ventes))
    else:
        st.write("Aucune vente enregistrée.")
