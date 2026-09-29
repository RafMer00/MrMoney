import smtplib
import sqlite3
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd

def send_monthly_report():
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")
    recipient_email = os.getenv("REPORT_RECIPIENT", sender_email)

    if not sender_email or not sender_password:
        print("[Scheduler] Configurazione email assente. Report saltato.")
        return

    # Calcolo mese precedente
    today = datetime.now()
    first_day_current_month = today.replace(day=1)
    last_day_prev_month = first_day_current_month - timedelta(days=1)
    start_prev_month = last_day_prev_month.replace(day=1)

    conn = sqlite3.connect("budget.db")
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()

    if df.empty:
        body = "Nessuna transazione registrata nel mese scorso."
    else:
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_prev_month) & (df['date'] <= last_day_prev_month)
        m_df = df.loc[mask]

        inc = m_df[m_df['type'] == 'Entrata']['amount'].sum()
        exp = m_df[m_df['type'] == 'Uscita']['amount'].sum()
        cat_exp = m_df[m_df['type'] == 'Uscita'].groupby('category')['amount'].sum().to_dict()

        body = f"""Ciao! Ecco il report spese per il mese di {start_prev_month.strftime('%B %Y')}:

- Entrate Totali: € {inc:.2f}
- Uscite Totali:  € {exp:.2f}
- Risparmio Netto: € {(inc - exp):.2f}

Spese per Categoria:
"""
        for cat, amt in cat_exp.items():
            body += f"  • {cat}: € {amt:.2f}\n"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Report Mensile Spese - {start_prev_month.strftime('%m/%Y')}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("[Scheduler] Report mensile inviato con successo!")
    except Exception as e:
        print(f"[Scheduler] Errore invio email: {e}")