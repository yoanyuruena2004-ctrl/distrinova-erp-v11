"""
database.py — Conexión a Supabase para DistriNova ERP
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

load_dotenv()  # Lee el archivo .env

# ── Obtener claves (local con .env o desde Streamlit Cloud)
def get_supabase() -> Client:
    # En Streamlit Cloud las claves van en st.secrets
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")

    if not url or not key:
        st.error("❌ Faltan las claves de Supabase. Revisa tu archivo .env")
        st.stop()

    return create_client(url, key)

# ── Instancia global reutilizable
@st.cache_resource
def supabase() -> Client:
    return get_supabase()
