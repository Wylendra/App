import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION (Identique) ---
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

st.title("📊 Portfolio Tracker Pro v2.0")
tabs = st.tabs(["📊 Analyse", "💼 Positions", "💸 Ventes", "📈 Benchmark"])

# --- ONGLET ANALYSE (Identique) ---
with tabs[0]:
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

# --- ONGLET POSITIONS (Avec Suppression) ---
with tabs[1]:
    st.subheader("Positions Actuelles")
    data_list = []
    lat_totale, investi_total = 0, 0
    for t in list(st.session_state.portefeuille.keys()):
        try:
            i = st.session_state.portefeuille[t]
            p_live = yf.Ticker(t).fast_info['last_price']
            val_actuelle, val_achat = p_live * i['qty'], i['pru'] * i['qty']
            pf = val_actuelle - val_achat
            lat_totale += pf; investi_total += val_achat
            col_info, col_del = st.columns([5, 1])
            col_info.write(f"{ICONES.get(t, '📈')} **{t}** | Live: {p_live:.2f}€ | PRU: {i['pru']:.2f}€ | Val: {val_actuelle:.2f}€ | Perf: {pf:+.2f}€")
            if col_del.button("🗑️", key=f"del_{t}"):
                del st.session_state.portefeuille[t]
                sauvegarder_donnees(st.session_state.portefeuille, st.session_state.ventes)
                st.rerun()
        except: continue
    if investi_total > 0:
        st.metric("Plus-Value Latente", f"{lat_totale:+.2f} €", f"{(lat_totale/investi_total*100):+.2f}%")

# --- ONGLET VENTES (Avec Annulation) ---
with tabs[2]:
    st.subheader("ENREGISTRER UNE VENTE")
    if st.session_state.portefeuille:
        v_t = st.selectbox("Action à vendre", list(st.session_state.portefeuille.keys()))
        colv1, colv2 = st.columns(2)
        pv = colv1.number_input("Prix Vente (€)", min_value=0.0)
        qv = colv2.number_input("Qté à vendre", min_value=0.0)
        if st.button("VENDRE"):
            if qv <= st.session_state.portefeuille[v_t]['qty']:
                pa_v = st.session_state.portefeuille[v_t]['pru']
                st.session_state.ventes.append({'ticker': v_t, 'gain': (pv-pa_v)*qv, 'date': str(datetime.now().date()), 'pru_achat': pa_v, 'qty_vendu': qv})
                st.session_state.portefeuille[v_t]['qty'] -= qv
                if st.session_state.portefeuille[v_t]['qty'] <= 0: del st.session_state.portefeuille[v_t]
                sauvegarder_donnees(st.session_state.portefeuille, st.session_state.ventes)
                st.rerun()
    st.write("Historique")
    for idx, v in enumerate(st.session_state.ventes):
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{v['ticker']}** | Gain: {v['gain']:+.2f}€ | Date: {v['date']}")
        if c2.button("Annuler", key=f"undo_{idx}"):
            v_pop = st.session_state.ventes.pop(idx)
            if v_pop['ticker'] in st.session_state.portefeuille: st.session_state.portefeuille[v_pop['ticker']]['qty'] += v_pop['qty_vendu']
            else: st.session_state.portefeuille[v_pop['ticker']] = {'pru': v_pop['pru_achat'], 'qty': v_pop['qty_vendu'], 'date': v_pop['date']}
            sauvegarder_donnees(st.session_state.portefeuille, st.session_state.ventes)
            st.rerun()

# --- ONGLET BENCHMARK (LA MODIFICATION DEMANDÉE) ---
with tabs[3]:
    st.subheader("COMPARAISON DES PERFORMANCES RÉELLES")
    if st.button("📊 CALCULER ET TRACER LES PERFORMANCES"):
        if not st.session_state.portefeuille:
            st.warning("Ajoutez des positions pour voir le graphique.")
        else:
            with st.spinner("Récupération des données historiques..."):
                try:
                    plt.style.use('dark_background')
                    debut_annee = "2026-01-01"
                    
                    # 1. Benchmark (Indice World)
                    bench_df = yf.download(BENCHMARK_TICKER, start=debut_annee)
                    bench_close = bench_df['Close'].squeeze()
                    perc_w = ((bench_close / bench_close.iloc[0]) - 1) * 100

                    # 2. Portefeuille (Positions actuelles)
                    df_valeur_port = pd.Series(0.0, index=bench_close.index)
                    val_initiale_janvier = 0
                    for t, info in st.session_state.portefeuille.items():
                        asset_data = yf.download(t, start=debut_annee)['Close'].squeeze()
                        asset_aligned = asset_data.reindex(bench_close.index).ffill().bfill()
                        df_valeur_port += (asset_aligned * info['qty'])
                        val_initiale_janvier += (asset_aligned.iloc[0] * info['qty'])

                    # 3. Ventes réalisées
                    df_gains_ventes = pd.Series(0.0, index=bench_close.index)
                    for v in st.session_state.ventes:
                        if v['date'] >= debut_annee:
                            date_v = pd.to_datetime(v['date'])
                            mask = df_gains_ventes.index >= date_v
                            df_gains_ventes.loc[mask] += v['gain']

                    # Calcul des courbes %
                    port_perf_excl = ((df_valeur_port / val_initiale_janvier) - 1) * 100
                    port_perf_incl = (((df_valeur_port + df_gains_ventes) / val_initiale_janvier) - 1) * 100

                    # Affichage des métriques
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Perf. Positions YTD", f"{port_perf_excl.iloc[-1]:+.2f}%")
                    c2.metric("Bilan Global YTD", f"{port_perf_incl.iloc[-1]:+.2f}%")
                    c3.metric("MSCI World YTD", f"{perc_w.iloc[-1]:+.2f}%")

                    # Le Graphique
                    fig, ax = plt.subplots(figsize=(10, 6))
                    fig.patch.set_facecolor('#1a1b26')
                    ax.set_facecolor('#1a1b26')
                    ax.plot(perc_w, color="#f7768e", label="MSCI World (Benchmark)", alpha=0.7)
                    ax.plot(port_perf_excl, color="#7aa2f7", label="Positions (Latent YTD)", linestyle="--")
                    ax.plot(port_perf_incl, color="#9ece6a", label="Bilan Global (Ventes Incl.)", linewidth=2.5)
                    ax.legend(); ax.grid(alpha=0.2)
                    st.pyplot(fig)
                except Exception as e:
                    st.error(f"Erreur de calcul : {e}")
