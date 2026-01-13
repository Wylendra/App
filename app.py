import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import json
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

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

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def charger_donnees_gsheet(user):
    try:
        # Lecture de la feuille "Donnees" (ttl=0 pour avoir les données réelles)
        df = conn.read(worksheet="Donnees", ttl=0)
        user_row = df[df['username'] == user.lower()]
        if not user_row.empty:
            data = json.loads(user_row.iloc[0]['json_data'])
            return data.get("portefeuille", {}), data.get("ventes", [])
    except Exception as e:
        pass
    return {}, []

def sauvegarder_donnees_gsheet(user, portefeuille, ventes):
    try:
        # 1. Lire les données existantes pour ne pas écraser les autres utilisateurs
        try:
            df = conn.read(worksheet="Donnees", ttl=0)
        except:
            df = pd.DataFrame(columns=["username", "json_data"])

        # 2. Préparer le JSON
        new_json = json.dumps({"portefeuille": portefeuille, "ventes": ventes})
        
        # 3. Mise à jour ou ajout
        if user.lower() in df['username'].values:
            df.loc[df['username'] == user.lower(), 'json_data'] = new_json
        else:
            new_line = pd.DataFrame([{"username": user.lower(), "json_data": new_json}])
            df = pd.concat([df, new_line], ignore_index=True)
        
        # 4. Envoi vers Google Sheets
        conn.update(worksheet="Donnees", data=df)
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")

# --- INITIALISATION DE LA SESSION ---
st.set_page_config(page_title="Portfolio Tracker Pro", layout="wide")

if 'current_user' not in st.session_state:
    st.session_state.current_user = "Invite"
    p, v = charger_donnees_gsheet("Invite")
    st.session_state.portefeuille, st.session_state.ventes = p, v

# --- SIDEBAR : PROFILS ---
with st.sidebar:
    st.header("👤 COMPTE")
    nom_saisi = st.text_input("Nom d'utilisateur :", value=st.session_state.current_user)
    if st.button("Charger mon Profil"):
        st.session_state.current_user = nom_saisi
        p, v = charger_donnees_gsheet(nom_saisi)
        st.session_state.portefeuille, st.session_state.ventes = p, v
        st.rerun()
    st.write(f"Utilisateur actuel : **{st.session_state.current_user}**")

# --- INTERFACE PRINCIPALE ---
st.title(f"📊 Portfolio Tracker Pro - {st.session_state.current_user}")
tabs = st.tabs(["📊 Analyse", "💼 Positions", "💸 Ventes", "📈 Benchmark"])

# --- ONGLET ANALYSE ---
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
        sauvegarder_donnees_gsheet(st.session_state.current_user, st.session_state.portefeuille, st.session_state.ventes)
        st.rerun()

# --- ONGLET POSITIONS ---
with tabs[1]:
    st.subheader("Positions Actuelles")
    lat_totale, investi_total = 0, 0
    p_keys = list(st.session_state.portefeuille.keys())
    for t in p_keys:
        try:
            i = st.session_state.portefeuille[t]
            p_live = yf.Ticker(t).fast_info['last_price']
            val_actuelle, val_achat = p_live * i['qty'], i['pru'] * i['qty']
            pf = val_actuelle - val_achat
            lat_totale += pf; investi_total += val_achat
            c_info, c_del = st.columns([5, 1])
            c_info.write(f"{ICONES.get(t, '📈')} **{t}** | **Qté: {i['qty']}** | Live: {p_live:.2f}€ | PRU: {i['pru']:.2f}€ | Perf: {pf:+.2f}€")
            if c_del.button("🗑️", key=f"del_{t}"):
                del st.session_state.portefeuille[t]
                sauvegarder_donnees_gsheet(st.session_state.current_user, st.session_state.portefeuille, st.session_state.ventes)
                st.rerun()
        except: continue
    if investi_total > 0:
        st.divider()
        st.metric("Plus-Value Latente Totale", f"{lat_totale:+.2f} €", f"{(lat_totale/investi_total*100):+.2f}%")

# --- ONGLET VENTES ---
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
                sauvegarder_donnees_gsheet(st.session_state.current_user, st.session_state.portefeuille, st.session_state.ventes)
                st.rerun()
    st.write("Historique")
    for idx, v in enumerate(st.session_state.ventes):
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{v['ticker']}** | Gain: {v['gain']:+.2f}€ | Date: {v['date']}")
        if c2.button("Annuler", key=f"undo_{idx}"):
            v_p = st.session_state.ventes.pop(idx)
            if v_p['ticker'] in st.session_state.portefeuille: st.session_state.portefeuille[v_p['ticker']]['qty'] += v_p['qty_vendu']
            else: st.session_state.portefeuille[v_p['ticker']] = {'pru': v_p['pru_achat'], 'qty': v_p['qty_vendu'], 'date': v_p['date']}
            sauvegarder_donnees_gsheet(st.session_state.current_user, st.session_state.portefeuille, st.session_state.ventes)
            st.rerun()

# --- ONGLET BENCHMARK ---
with tabs[3]:
    if st.button("📊 CALCULER LES PERFORMANCES"):
        try:
            plt.style.use('dark_background')
            debut_annee = "2026-01-01"
            bench_df = yf.download(BENCHMARK_TICKER, start=debut_annee)
            bench_close = bench_df['Close'].squeeze()
            perc_w = ((bench_close / bench_close.iloc[0]) - 1) * 100
            df_valeur_port = pd.Series(0.0, index=bench_close.index)
            val_init = 0
            for t, info in st.session_state.portefeuille.items():
                asset_data = yf.download(t, start=debut_annee)['Close'].squeeze()
                asset_aligned = asset_data.reindex(bench_close.index).ffill().bfill()
                df_valeur_port += (asset_aligned * info['qty'])
                val_init += (asset_aligned.iloc[0] * info['qty'])
            df_gains_ventes = pd.Series(0.0, index=bench_close.index)
            for v in st.session_state.ventes:
                if v['date'] >= debut_annee:
                    df_gains_ventes.loc[df_gains_ventes.index >= pd.to_datetime(v['date'])] += v['gain']
            p_excl = ((df_valeur_port / val_init) - 1) * 100
            p_incl = (((df_valeur_port + df_gains_ventes) / val_init) - 1) * 100
            fig, ax = plt.subplots(figsize=(10, 6)); ax.plot(perc_w, color="#f7768e", label="MSCI World")
            ax.plot(p_excl, color="#7aa2f7", linestyle="--", label="Positions (Latent)")
            ax.plot(p_incl, color="#9ece6a", linewidth=2, label="Bilan Global"); ax.legend(); st.pyplot(fig)
        except: st.error("Erreur lors du calcul du benchmark.")
