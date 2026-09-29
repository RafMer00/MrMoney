import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from db import (
    init_db, get_initial_balance, set_initial_balance,
    add_category, get_categories, add_transaction,
    get_transactions_df, get_frequent_and_recent_titles
)
from mailer import send_monthly_report

st.set_page_config(page_title="Gestione Finanze", page_icon="💰", layout="wide")

# Inizializza DB e Scheduler background per email il 1° del mese alle 08:00
init_db()

@st.cache_resource
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_monthly_report, 'cron', day=1, hour=8, minute=0)
    scheduler.start()
    return scheduler

start_scheduler()

# Sidebar: Saldo Iniziale & Nuove Categorie
with st.sidebar:
    st.header("⚙️ Impostazioni")
    current_init_balance = get_initial_balance()
    new_init_balance = st.number_input("Saldo iniziale (€)", value=current_init_balance, step=50.0)
    if st.button("Salva Saldo Iniziale"):
        set_initial_balance(new_init_balance)
        st.success("Saldo iniziale aggiornato!")
        st.rerun()

    st.subheader("Crea Nuova Categoria")
    new_cat = st.text_input("Nome Categoria")
    if st.button("Aggiungi Categoria"):
        if new_cat:
            add_category(new_cat)
            st.success(f"Categoria '{new_cat}' aggiunta!")
            st.rerun()

# Dati
df = get_transactions_df()
total_income = df[df['type'] == 'Entrata']['amount'].sum() if not df.empty else 0.0
total_expenses = df[df['type'] == 'Uscita']['amount'].sum() if not df.empty else 0.0
current_balance = get_initial_balance() + total_income - total_expenses

# Metriche Principali
col1, col2, col3 = st.columns(3)
col1.metric("Saldo Attuale", f"€ {current_balance:,.2f}")
col2.metric("Totale Guadagni", f"€ {total_income:,.2f}")
col3.metric("Totale Spese", f"€ {total_expenses:,.2f}")

tab_insert, tab_stats, tab_advisor = st.tabs(["➕ Registra Spesa/Entrata", "📊 Statistiche & Grafici", "💡 Consulente Risparmio"])

# TAB 1: Inserimento rapido
with tab_insert:
    st.subheader("Inserisci Movimento")
    c1, c2 = st.columns(2)
    with c1:
        t_type = st.radio("Tipo", ["Uscita", "Entrata"], horizontal=True)
        t_amount = st.number_input("Importo (€)", min_value=0.01, step=1.0, format="%.2f")
        t_date = st.date_input("Data", value=date.today())

    with c2:
        freq_titles, rec_titles = get_frequent_and_recent_titles()
        all_hints = list(dict.fromkeys(rec_titles + freq_titles))
        
        st.markdown("**Titoli suggeriti:**")
        selected_hint = st.selectbox("Seleziona da frequenti/recenti:", ["-- Nessuno / Scrivi tu --"] + all_hints)
        custom_title = st.text_input("Titolo / Descrizione:", value="" if selected_hint.startswith("--") else selected_hint)
        
        categories = get_categories()
        selected_category = st.selectbox("Categoria", categories)

    if st.button("Salva Movimento", use_container_width=True):
        final_title = custom_title if custom_title else "Senza titolo"
        add_transaction(str(t_date), t_type, t_amount, final_title, selected_category)
        st.success("Registrato con successo!")
        st.rerun()

    if not df.empty:
        st.markdown("### Ultime transazioni")
        st.dataframe(df[['date', 'type', 'amount', 'title', 'category']].head(10), use_container_width=True)

# TAB 2: Statistiche
with tab_stats:
    if df.empty:
        st.info("Nessuna transazione disponibile. Aggiungi la prima spesa per generare i grafici!")
    else:
        expenses_df = df[df['type'] == 'Uscita'].copy()

        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Uscite per Categoria")
            if not expenses_df.empty:
                cat_chart = px.pie(expenses_df, values='amount', names='category', hole=0.4)
                st.plotly_chart(cat_chart, use_container_width=True)
            else:
                st.write("Nessuna uscita registrata.")

        with g2:
            st.subheader("Spese nel Tempo (per Giorno)")
            if not expenses_df.empty:
                daily_exp = expenses_df.groupby('date')['amount'].sum().reset_index()
                line_chart = px.bar(daily_exp, x='date', y='amount', labels={'amount': 'Spesa (€)', 'date': 'Data'})
                st.plotly_chart(line_chart, use_container_width=True)

        g3, g4 = st.columns(2)
        with g3:
            st.subheader("Entrate vs Uscite")
            flow_df = df.groupby('type')['amount'].sum().reset_index()
            bar_flow = px.bar(flow_df, x='type', y='amount', color='type', color_discrete_map={'Entrata':'#2ecc71', 'Uscita':'#e74c3c'})
            st.plotly_chart(bar_flow, use_container_width=True)

        with g4:
            st.subheader("Top 5 Spese Più Onerose")
            if not expenses_df.empty:
                top_exp = expenses_df.sort_values(by='amount', ascending=False).head(5)
                top_bar = px.bar(top_exp, x='title', y='amount', color='category')
                st.plotly_chart(top_bar, use_container_width=True)

# TAB 3: Analisi e Suggerimenti
with tab_advisor:
    st.subheader("Analisi Gestione Spese")
    if df.empty:
        st.write("Registra qualche spesa per sbloccare l'analisi automatica.")
    else:
        expenses_df = df[df['type'] == 'Uscita']
        savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
        
        st.markdown(f"**Tasso di Risparmio Attuale:** `{savings_rate:.1f}%`")
        
        if savings_rate < 15:
            st.warning("⚠️ Stai risparmiando meno del 15% delle tue entrate. Cerca di tagliare le spese non essenziali.")
        elif savings_rate >= 30:
            st.success("🌟 Ottimo lavoro! Il tuo tasso di risparmio è superiore al 30%.")
            
        if not expenses_df.empty:
            top_category = expenses_df.groupby('category')['amount'].sum().idxmax()
            top_cat_amount = expenses_df.groupby('category')['amount'].sum().max()
            st.markdown(f"- **Categoria di spesa principale:** `{top_category}` con un totale di **€ {top_cat_amount:,.2f}**.")
            st.markdown(f"- **Regola 50/30/20 suggerita:** Mantieni le necessità fisse (famiglia) entro il 50%, le spese personali (io, daniela) entro il 30% e destina il restante 20% a fondo cassa o investimenti.")