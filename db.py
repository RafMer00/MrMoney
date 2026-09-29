import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Recupera credenziali dai Secrets di Streamlit o da variabili d'ambiente
def get_supabase_client() -> Client:
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))
    if not url or not key:
        st.error("Credenziali Supabase mancanti! Configurale nei Secrets di Streamlit.")
        st.stop()
    return create_client(url, key)

supabase = get_supabase_client()

def get_initial_balance():
    try:
        res = supabase.table("settings").select("value").eq("key", "initial_balance").execute()
        if res.data:
            return float(res.data[0]["value"])
    except Exception as e:
        print(f"Errore lettura saldo: {e}")
    return 0.0

def set_initial_balance(amount):
    try:
        supabase.table("settings").upsert(
            {"key": "initial_balance", "value": str(amount)},
            on_conflict="key"
        ).execute()
    except Exception as e:
        st.error(f"Errore durante il salvataggio del saldo: {e}")
        
def add_category(name):
    clean_name = name.strip()
    if clean_name:
        try:
            supabase.table("categories").insert({"name": clean_name}).execute()
        except Exception:
            pass  # Ignora se esiste già

def get_categories():
    res = supabase.table("categories").select("name").order("id", desc=False).execute()
    return [r["name"] for r in res.data] if res.data else ["io", "daniela", "famiglia"]

def add_transaction(date_str, trans_type, amount, title, category):
    data = {
        "date": str(date_str),
        "type": trans_type,
        "amount": float(amount),
        "title": title.strip(),
        "category": category
    }
    supabase.table("transactions").insert(data).execute()

def get_transactions_df():
    res = supabase.table("transactions").select("*").order("date", desc=True).order("id", desc=True).execute()
    if not res.data:
        return pd.DataFrame(columns=["id", "date", "type", "amount", "title", "category"])
    df = pd.DataFrame(res.data)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"])
    return df

def get_frequent_and_recent_titles():
    df = get_transactions_df()
    if df.empty:
        return [], []
    frequent = df["title"].value_counts().head(5).index.tolist()
    recent = df["title"].drop_duplicates().head(5).tolist()
    return frequent, recent