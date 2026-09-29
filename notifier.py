import requests
import sqlite3
import os
from datetime import datetime, timedelta
import pandas as pd

# Inserisci il token del bot e il tuo chat_id (oppure mettili nei Secrets di Streamlit)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "INSERISCI_QUI_IL_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "INSERISCI_QUI_IL_TUO_ID")

def send_monthly_report():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Notifier] Token o Chat ID mancanti.")
        return

    today = datetime.now()
    first_day_current_month = today.replace(day=1)
    last_day_prev_month = first_day_current_month - timedelta(days=1)
    start_prev_month = last_day_prev_month.replace(day=1)

    conn = sqlite3.connect("budget.db")
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()

    if df.empty:
        msg = "📊 *Report Spese Mensile*\nNessun movimento registrato nel mese appena concluso."
    else:
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_prev_month) & (df['date'] <= last_day_prev_month)
        m_df = df.loc[mask]

        inc = m_df[m_df['type'] == 'Entrata']['amount'].sum()
        exp = m_df[m_df['type'] == 'Uscita']['amount'].sum()
        cat_exp = m_df[m_df['type'] == 'Uscita'].groupby('category')['amount'].sum().to_dict()

        msg = f"📊 *Report Mese di {start_prev_month.strftime('%B %Y')}*\n\n"
        msg += f"🟢 *Entrate:* € {inc:,.2f}\n"
        msg += f"🔴 *Uscite:*  € {exp:,.2f}\n"
        msg += f"💰 *Netto:*   € {(inc - exp):,.2f}\n\n"
        msg += "*Dettaglio categorie:*\n"
        for cat, amt in cat_exp.items():
            msg += f"• `{cat}`: € {amt:,.2f}\n"

    # Chiamata API standard verso Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)