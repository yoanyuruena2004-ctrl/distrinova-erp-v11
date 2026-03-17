"""
database.py — Conexión a Supabase para DistriNova ERP
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")

    # Diagnóstico claro si faltan las claves
    if not url or url.strip() == "" or "tu_supabase" in url.lower():
        st.error("❌ **SUPABASE_URL** no está configurada.")
        st.info("""
**Para arreglarlo:**

1. Abre (o crea) el archivo: `distrinova_v11/.streamlit/secrets.toml`
2. Pega exactamente esto con tus datos reales:
```toml
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR..."
GEMINI_API_KEY = "AIzaSy..."
```
3. Guarda el archivo y **reinicia** el servidor: `Ctrl+C` y luego `streamlit run app.py`

Los valores los encuentras en tu proyecto Supabase → Settings → API.
""")
        st.stop()

    if not key or key.strip() == "" or "tu_supabase" in key.lower():
        st.error("❌ **SUPABASE_KEY** no está configurada. Revisa `.streamlit/secrets.toml`.")
        st.stop()

    try:
        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"❌ Error conectando a Supabase: `{e}`")
        st.info("Verifica que la URL empiece con `https://` y termine en `.supabase.co`")
        st.stop()

@st.cache_resource
def supabase() -> Client:
    return get_supabase()
