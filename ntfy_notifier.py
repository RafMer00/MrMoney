import sqlite3
import os
import requests
from datetime import datetime, timedelta
import pandas as pd

# Inserisci il nome del canale segreto creato sull'app iPhone
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "mie-spese-famiglia-99214")

def send_monthly_report():
    if not NTFY_TOPIC:
        print("[ntfy] Topic non configurato.")
        return

    today = datetime.now()
    first_day_current_month = today.replace(day=1)
    last_day_prev_month = first_day_current_month - timedelta(days=1)
    start_prev_month = last_day_prev_month.replace(day=1)

    conn = sqlite3.connect("budget.db")
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()

    month_name = start_prev_month.strftime('%m/%Y')

    if df.empty:
        message = "Nessuna transazione registrata nel mese appena trascorso."
    else:
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_prev_month) & (df['date'] <= last_day_prev_month)
        m_df = df.loc[mask]

        inc = m_df[m_df['type'] == 'Entrata']['amount'].sum()
        exp = m_df[m_df['type'] == 'Uscita']['amount'].sum()
        cat_exp = m_df[m_df['type'] == 'Uscita'].groupby('category')['amount'].sum().to_dict()

        message = (
            f"Entrate: € {inc:,.2f}\n"
            f"Uscite:  € {exp:,.2f}\n"
            f"Risparmio: € {(inc - exp):,.2f}\n\n"
            "Dettaglio Spese:\n"
        )
        for cat, amt in cat_exp.items():
            message += f"• {cat}: € {amt:,.2f}\n"

    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        headers = {
            "Title": f"Report Spese {month_name}".encode('utf-8'),
            "Priority": "default",
            "Tags": "moneybag,chart_with_upwards_trend"
        }
        res = requests.post(url, data=message.encode('utf-8'), headers=headers)
        if res.status_code == 200:
            print("[ntfy] Notifica inviata con successo su iPhone!")
        else:
            print(f"[ntfy] Errore invio notifica: {res.status_code}")
    except Exception as e:
        print(f"[ntfy] Eccezione di rete: {e}")