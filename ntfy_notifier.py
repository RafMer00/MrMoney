import os
import requests
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from db import get_supabase_client

def send_monthly_report():
    # Recupera topic dai Secrets o env
    topic = st.secrets.get("NTFY_TOPIC", os.getenv("NTFY_TOPIC", "mie-spese-famiglia-99214"))
    supabase = get_supabase_client()

    today = datetime.now()
    first_day_curr = today.replace(day=1)
    last_day_prev = first_day_curr - timedelta(days=1)
    start_prev = last_day_prev.replace(day=1)
    month_name = start_prev.strftime('%m/%Y')

    res = supabase.table("transactions").select("*").execute()
    data = res.data or []

    if not data:
        message = "Nessun movimento registrato."
    else:
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'])
        
        mask = (df['date'] >= start_prev) & (df['date'] <= last_day_prev)
        m_df = df.loc[mask]

        if m_df.empty:
            message = f"Nessuna spesa o entrata nel mese di {month_name}."
        else:
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
        url = f"https://ntfy.sh/{topic}"
        headers = {
            "Title": f"Report Spese {month_name}".encode('utf-8'),
            "Priority": "default",
            "Tags": "moneybag,bar_chart"
        }
        requests.post(url, data=message.encode('utf-8'), headers=headers)
    except Exception as e:
        print(f"Errore invio notifica: {e}")