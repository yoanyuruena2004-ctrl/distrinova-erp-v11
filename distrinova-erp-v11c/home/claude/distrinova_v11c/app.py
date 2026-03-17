"""DistriNova ERP v10.0 — Cadena completa: Clientes · Almacenamiento · Órdenes · Turbos · Margen%"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests, math, re, os
from database import supabase
from datetime import datetime, date, timedelta

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_OK = True
except ImportError:
    FOLIUM_OK = False

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(page_title="DistriNova ERP", page_icon="🚚",
                   layout="wide", initial_sidebar_state="expanded")

DEFAULTS = {
    "tarifa_km": 3000, "recargo_nocturno_pct": 30,
    "tarifa_almacenamiento": 500, "tarifa_alistamiento": 200,
    "tarifa_manipulacion": 150, "tarifa_admin_pct": 5,
    "margen_pct": 20,
    "tarifa_alm_ton_dia": 15000,
    "tarifa_alm_m3_dia": 5000,
    "cap_almacen": 5000, "stock_min": 50,
    "vida_util_dias": 3, "alerta_vence_dias": 2,
    "costo_conductor_dia": 80000, "costo_combustible_km": 450,
    "costo_peaje_promedio": 15000, "costo_mantenimiento_km": 120,
    "costos_indirectos_pct": 35,  # depreciación, seguros, prestaciones, admin CEDI
}
for k, v in DEFAULTS.items():
    if f"cfg_{k}" not in st.session_state:
        st.session_state[f"cfg_{k}"] = v

def cfg(k): return st.session_state.get(f"cfg_{k}", DEFAULTS.get(k, 0))

CEDIS = ["Medellín", "Santa Rosa", "Taraza"]
CEDI_COORDS = {
    "Medellín":  [6.2442, -75.5812],
    "Santa Rosa": [6.6458, -75.4627],
    "Taraza":    [7.5731, -75.4058],
}
TIPO_COLOR = {"proveedor": "red", "fabricante": "orange", "mayorista": "blue", "minorista": "green"}
TIPO_ICON  = {"proveedor": "industry", "fabricante": "cogs", "mayorista": "building", "minorista": "shopping-cart"}

# ══════════════════════════════════════════════════════
# FÓRMULAS
# ══════════════════════════════════════════════════════
def calcular_flete(km, furgs=1, nocturno=False, ida_vuelta=True):
    km_total = float(km) * 2 if ida_vuelta else float(km)
    base = km_total * cfg("tarifa_km") * furgs
    return int(base * (1 + cfg("recargo_nocturno_pct") / 100)) if nocturno else int(base)

def calcular_costos_operativos(km, furgs=1, ida_vuelta=True):
    km_total = float(km) * 2 if ida_vuelta else float(km)
    costo_directo = int(km_total * furgs * (cfg("costo_combustible_km") + cfg("costo_mantenimiento_km"))
               + furgs * cfg("costo_conductor_dia") + cfg("costo_peaje_promedio") * furgs)
    # Costos indirectos: depreciación, seguros, prestaciones sociales, admin CEDI
    costo_indirecto = int(costo_directo * cfg("costos_indirectos_pct") / 100)
    return costo_directo + costo_indirecto

def aplicar_margen(subtotal):
    m = int(subtotal * cfg("margen_pct") / 100)
    return m, subtotal + m

def stock_cedi(df, nom):
    if df is None or df.empty or "cedi" not in df.columns or "stock" not in df.columns: return 0
    r = df.loc[df["cedi"] == nom, "stock"]
    return int(r.values[0]) if len(r) > 0 else 0

def stock_total(df):
    if df is None or df.empty or "stock" not in df.columns: return 0
    return int(df["stock"].sum())

def calcular_capacidad(aw, al, ah, ca, cl, ch, arrume):
    if ca <= 0 or cl <= 0 or ch <= 0: return 0
    return int(aw / ca) * int(al / cl) * min(int(ah / ch), arrume)

def dias_almacenado(fecha_ingreso_str, fecha_salida_str=None):
    try:
        fi = date.fromisoformat(str(fecha_ingreso_str)[:10])
        fs = date.fromisoformat(str(fecha_salida_str)[:10]) if fecha_salida_str else date.today()
        return max(0, (fs - fi).days)
    except:
        return 0

def costo_almacenamiento(peso_ton, dias, tarifa_ton_dia=None):
    t = tarifa_ton_dia if tarifa_ton_dia else cfg("tarifa_alm_ton_dia")
    return int(float(peso_ton) * dias * t)

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&family=Barlow+Condensed:wght@600;700;800&display=swap');
:root{--bg:#060D18;--bg2:#0C1829;--bg3:#111F33;--bg4:#16263D;
  --border:rgba(255,255,255,.07);--border2:rgba(30,136,229,.2);
  --txt:#C8D8EA;--txt2:#5A7A99;--txt3:#334D66;
  --accent:#1E88E5;--accent2:#FF8C00;--green:#00C97A;--red:#FF4444;--yellow:#FFB800;--purple:#9C6FE4;
  --font:'Space Grotesk',sans-serif;--mono:'JetBrains Mono',monospace;--cond:'Barlow Condensed',sans-serif}
html,body,[class*="css"]{font-family:var(--font)}
.stApp{background:var(--bg)!important;color:var(--txt)}
.main .block-container{padding:0!important;max-width:100%!important}
section[data-testid="stSidebar"]{background:var(--bg2)!important;border-right:1px solid var(--border)!important;width:264px!important}
section[data-testid="stSidebar"]>div{padding:0!important}
#MainMenu,footer,header{visibility:hidden!important}
.stDeployButton{display:none!important}
[data-testid="stDecoration"]{display:none!important}
[data-testid="metric-container"]{background:var(--bg3)!important;border:1px solid var(--border)!important;border-radius:10px!important;padding:16px 20px!important;transition:border-color .2s}
[data-testid="metric-container"]:hover{border-color:var(--border2)!important}
[data-testid="stMetricLabel"]{color:var(--txt2)!important;font-size:10px!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:1.5px!important}
[data-testid="stMetricValue"]{color:var(--txt)!important;font-size:24px!important;font-weight:700!important;font-family:var(--mono)!important}
.stDataFrame{border-radius:10px!important;overflow:hidden!important;border:1px solid var(--border)!important}
.stButton>button{background:var(--bg4)!important;color:var(--txt)!important;border:1px solid var(--border2)!important;border-radius:8px!important;font-family:var(--font)!important;font-weight:600!important;font-size:13px!important;transition:all .2s!important}
.stButton>button:hover{background:var(--accent)!important;border-color:var(--accent)!important;color:white!important;transform:translateY(-1px)!important}
.stTabs [data-baseweb="tab-list"]{background:var(--bg2)!important;border-bottom:1px solid var(--border)!important;padding:0 4px!important}
.stTabs [data-baseweb="tab"]{color:var(--txt2)!important;font-size:11px!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:1px!important;padding:12px 18px!important;border-bottom:2px solid transparent!important;background:transparent!important}
.stTabs [aria-selected="true"]{color:var(--txt)!important;border-bottom-color:var(--accent2)!important}
.stProgress>div>div{background:linear-gradient(90deg,var(--accent),#42A5F5)!important;border-radius:4px!important}
.stProgress>div{background:var(--bg4)!important;border-radius:4px!important;height:6px!important}
.stSelectbox>div>div,.stNumberInput>div>div,.stTextInput>div>div,.stTextArea>div>div{background:var(--bg3)!important;border:1px solid var(--border)!important;border-radius:8px!important;color:var(--txt)!important}
hr{border-color:var(--border)!important;margin:20px 0!important}
::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-track{background:var(--bg2)}::-webkit-scrollbar-thumb{background:var(--bg4);border-radius:4px}
.dn-logo{padding:20px 20px 14px;border-bottom:1px solid var(--border)}
.dn-logo-title{font-family:var(--cond);font-size:26px;font-weight:800;letter-spacing:1px;line-height:1;color:white}
.dn-logo-title span{color:var(--accent2)}
.dn-logo-sub{font-size:10px;color:var(--txt3);text-transform:uppercase;letter-spacing:2px;margin-top:3px}
.dn-badge{display:inline-flex;align-items:center;gap:5px;background:rgba(0,201,122,.08);color:var(--green);border:1px solid rgba(0,201,122,.2);border-radius:20px;font-size:10px;font-weight:600;padding:3px 10px;margin-top:8px;letter-spacing:.5px}
.dn-mod-hdr{padding:14px 18px 5px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:2.5px;color:var(--txt3);display:flex;align-items:center;gap:8px}
.dn-mod-hdr::after{content:'';flex:1;height:1px;background:var(--border)}
.dn-module-banner{margin:0;padding:26px 32px 18px;background:linear-gradient(135deg,var(--bg2) 0%,var(--bg) 100%);border-bottom:1px solid var(--border);position:relative;overflow:hidden}
.dn-module-banner::before{content:attr(data-label);position:absolute;right:32px;top:50%;transform:translateY(-50%);font-family:var(--cond);font-size:72px;font-weight:800;color:rgba(255,255,255,.025);letter-spacing:4px;pointer-events:none}
.dn-module-tag{display:inline-block;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:2px;padding:3px 10px;border-radius:4px;margin-bottom:8px}
.tag-wms{background:rgba(30,136,229,.15);color:#42A5F5;border:1px solid rgba(30,136,229,.2)}
.tag-tms{background:rgba(255,140,0,.12);color:#FFB74D;border:1px solid rgba(255,140,0,.2)}
.tag-fin{background:rgba(0,201,122,.10);color:#4CAF50;border:1px solid rgba(0,201,122,.2)}
.tag-sys{background:rgba(255,255,255,.05);color:var(--txt2);border:1px solid var(--border)}
.tag-ia{background:rgba(156,111,228,.15);color:#CE93D8;border:1px solid rgba(156,111,228,.3)}
.tag-cli{background:rgba(255,184,0,.12);color:#FFD54F;border:1px solid rgba(255,184,0,.2)}
.dn-content{padding:22px 32px}
.dn-section{background:var(--bg3);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:16px}
.dn-section-header{padding:11px 18px;border-bottom:1px solid var(--border);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--txt2);display:flex;align-items:center;justify-content:space-between}
.dn-section-body{padding:16px 18px}
.dn-form{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:20px}
.dn-form-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--txt2);margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.dn-alert{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;border-radius:8px;font-size:12px;font-weight:500;margin-bottom:8px;border:1px solid}
.dn-ok{background:rgba(0,201,122,.06);border-color:rgba(0,201,122,.2);color:#66BB6A}
.dn-warn{background:rgba(255,184,0,.06);border-color:rgba(255,184,0,.2);color:#FFC107}
.dn-err{background:rgba(255,68,68,.08);border-color:rgba(255,68,68,.2);color:#EF5350}
.dn-info{background:rgba(30,136,229,.06);border-color:rgba(30,136,229,.2);color:#42A5F5}
.dn-ia{background:rgba(156,111,228,.06);border-color:rgba(156,111,228,.2);color:#CE93D8}
.dn-cedi{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:18px;transition:all .2s}
.dn-cedi:hover{border-color:var(--border2);transform:translateY(-2px)}
.dn-cedi-tag{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--txt3);margin-bottom:6px}
.dn-cedi-name{font-family:var(--cond);font-size:20px;font-weight:700;color:white}
.dn-cedi-stock{font-family:var(--mono);font-size:30px;font-weight:700;color:var(--accent);margin:8px 0 3px}
.dn-cedi-bar{height:4px;background:var(--bg4);border-radius:4px;margin-top:10px;overflow:hidden}
.dn-cedi-fill{height:100%;border-radius:4px}
.dn-status{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:.5px}
.status-ok{background:rgba(0,201,122,.1);color:var(--green)}
.status-warn{background:rgba(255,184,0,.1);color:var(--yellow)}
.status-err{background:rgba(255,68,68,.1);color:var(--red)}
.status-info{background:rgba(30,136,229,.1);color:var(--accent)}
.dn-user{padding:14px 18px;border-top:1px solid var(--border);display:flex;align-items:center;gap:10px}
.dn-avatar{width:32px;height:32px;border-radius:50%;background:var(--bg4);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.dn-user-name{font-size:13px;font-weight:600;color:var(--txt)}
.dn-user-role{font-size:10px;color:var(--txt3)}
.ia-bubble-user{background:var(--bg4);border:1px solid var(--border);border-radius:12px 12px 4px 12px;padding:12px 16px;margin:8px 0 8px 40px;font-size:13px;line-height:1.5}
.ia-bubble-bot{background:rgba(156,111,228,.08);border:1px solid rgba(156,111,228,.2);border-radius:12px 12px 12px 4px;padding:12px 16px;margin:8px 40px 8px 0;font-size:13px;line-height:1.6}
.ia-name-user{font-size:10px;color:var(--txt3);text-align:right;margin-right:4px;text-transform:uppercase;letter-spacing:1px}
.ia-name-bot{font-size:10px;color:rgba(156,111,228,.6);margin-left:4px;text-transform:uppercase;letter-spacing:1px}
.veh-card{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:16px;position:relative;transition:all .2s}
.veh-card:hover{border-color:var(--border2)}
.veh-codigo{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--accent2);margin-bottom:6px}
.veh-tipo{font-family:var(--cond);font-size:18px;font-weight:700;color:white;margin-bottom:8px}
.veh-cap{font-family:var(--mono);font-size:26px;font-weight:700;color:var(--accent)}
.veh-dim{font-size:11px;color:var(--txt2);margin-top:3px}
.veh-status{position:absolute;top:14px;right:14px}
.fin-card{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:18px;margin-bottom:12px}
.fin-val{font-family:var(--mono);font-size:28px;font-weight:700}
.fin-lbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--txt2);margin-bottom:6px}
.cli-card{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:10px;transition:all .2s}
.cli-card:hover{border-color:rgba(30,136,229,.3)}
.cli-tipo{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:4px}
.cli-nombre{font-family:var(--cond);font-size:20px;font-weight:700;color:white}
.cli-info{font-size:11px;color:var(--txt2);margin-top:4px}
.os-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700}
.os-recoleccion{background:rgba(255,68,68,.1);color:#EF5350}
.os-transferencia{background:rgba(30,136,229,.1);color:#42A5F5}
.os-entrega_cedi{background:rgba(255,140,0,.1);color:#FFB74D}
.os-entrega_directa{background:rgba(0,201,122,.1);color:#66BB6A}
.reset-btn>button{background:rgba(255,68,68,.15)!important;border-color:rgba(255,68,68,.4)!important;color:#EF5350!important}
.reset-btn>button:hover{background:rgba(255,68,68,.35)!important;color:white!important}
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# DB FUNCTIONS
# ══════════════════════════════════════════════════════
def db_get(tabla, order="created_at", desc=True, limit=500):
    try:
        q = supabase().table(tabla).select("*")
        if order: q = q.order(order, desc=desc)
        if limit: q = q.limit(limit)
        r = q.execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except Exception as e:
        err_str = str(e)
        # Solo muestra error si no es "tabla vacía"
        if "Invalid URL" in err_str or "connection" in err_str.lower():
            st.warning(f"⚠️ Sin conexión a Supabase ({tabla}). Revisa `secrets.toml`.")
        return pd.DataFrame()

def get_inv():      return db_get("inventario", order="cedi", desc=False)
def get_desp():     return db_get("despachos")
def get_mov():      return db_get("movimientos", limit=100)
def get_lotes():    return db_get("lotes", order="fecha_vencimiento", desc=False)
def get_clientes(): return db_get("clientes", order="tipo", desc=False)
def get_alm_clientes(): return db_get("almacenamiento_clientes", order="fecha_ingreso", desc=False)
def get_ordenes():  return db_get("ordenes_servicio")
def get_pedidos_comerciales(): return db_get("pedidos_comerciales")

def get_rutas_db():
    df = db_get("rutas", order="km", desc=False)
    if df.empty:
        return pd.DataFrame([
            {"id":1,"municipio":"Santa Rosa de Osos","km":77.4, "tiempo_est":"1h 20m","salida_max":"03:40","lat":6.6458,"lon":-75.4627,"activa":True},
            {"id":2,"municipio":"Yarumal",           "km":122.4,"tiempo_est":"2h 10m","salida_max":"02:50","lat":7.0025,"lon":-75.5147,"activa":True},
            {"id":3,"municipio":"Valdivia",           "km":174.0,"tiempo_est":"3h 00m","salida_max":"02:00","lat":7.1692,"lon":-75.4397,"activa":True},
            {"id":4,"municipio":"Taraza",             "km":249.0,"tiempo_est":"4h 10m","salida_max":"00:50","lat":7.5731,"lon":-75.4058,"activa":True},
            {"id":5,"municipio":"Caucasia",           "km":283.0,"tiempo_est":"4h 45m","salida_max":"00:15","lat":7.9887,"lon":-75.1973,"activa":True},
            {"id":6,"municipio":"Coveñas",            "km":412.0,"tiempo_est":"6h 30m","salida_max":"22:30","lat":9.1667,"lon":-75.6833,"activa":True},
            {"id":7,"municipio":"Pereira",            "km":200.0,"tiempo_est":"3h 30m","salida_max":"01:30","lat":4.8087,"lon":-75.6906,"activa":True},
        ])
    return df

def get_vehiculos():
    df = db_get("vehiculos", order="codigo", desc=False)
    if df.empty:
        return pd.DataFrame([
            {"id":1,"codigo":"FRG-01","tipo":"Furgoneta","ancho_m":2.2,"largo_m":2.5,"alto_m":1.8,"arrume_max":3,"capacidad":168,"tarifa_km":3000,"estado":"Activo","notas":""},
            {"id":2,"codigo":"FRG-02","tipo":"Furgoneta","ancho_m":2.2,"largo_m":2.5,"alto_m":1.8,"arrume_max":3,"capacidad":168,"tarifa_km":3000,"estado":"Activo","notas":""},
            {"id":3,"codigo":"FRG-03","tipo":"Furgoneta","ancho_m":2.2,"largo_m":2.5,"alto_m":1.8,"arrume_max":3,"capacidad":168,"tarifa_km":3000,"estado":"Activo","notas":""},
            {"id":4,"codigo":"FRG-04","tipo":"Furgoneta","ancho_m":2.2,"largo_m":2.5,"alto_m":1.8,"arrume_max":3,"capacidad":168,"tarifa_km":3000,"estado":"Reserva","notas":""},
            {"id":5,"codigo":"TRB-01","tipo":"Turbo (Plataforma Doble)","ancho_m":4.0,"largo_m":4.0,"alto_m":2.7,"arrume_max":6,"capacidad":1000,"tarifa_km":6000,"estado":"Activo","notas":"Plataforma doble — 6 arrumes max"},
            {"id":6,"codigo":"TRB-02","tipo":"Turbo (Plataforma Doble)","ancho_m":4.0,"largo_m":4.0,"alto_m":2.7,"arrume_max":6,"capacidad":1000,"tarifa_km":6000,"estado":"Activo","notas":"Plataforma doble — 6 arrumes max"},
            {"id":7,"codigo":"TRB-03","tipo":"Turbo (Plataforma Doble)","ancho_m":4.0,"largo_m":4.0,"alto_m":2.7,"arrume_max":6,"capacidad":1000,"tarifa_km":6000,"estado":"Activo","notas":"Plataforma doble — 6 arrumes max"},
            {"id":8,"codigo":"TRB-04","tipo":"Turbo (Plataforma Doble)","ancho_m":4.0,"largo_m":4.0,"alto_m":2.7,"arrume_max":6,"capacidad":1000,"tarifa_km":6000,"estado":"Reserva","notas":"Emergencias"},
            {"id":9,"codigo":"TRB-05","tipo":"Turbo (Plataforma Doble)","ancho_m":4.0,"largo_m":4.0,"alto_m":2.7,"arrume_max":6,"capacidad":1000,"tarifa_km":6000,"estado":"Reserva","notas":"Emergencias"},
        ])
    return df

# ══════════════════════════════════════════════════════
# RESET SISTEMA
# ══════════════════════════════════════════════════════
def reset_sistema():
    db = supabase()
    tablas_borrar = ["ordenes_servicio","pedidos_comerciales","despachos","movimientos","lotes","ia_chat","almacenamiento_clientes"]
    tablas_limpiar_legacy = ["pedidos"]
    for t in tablas_borrar + tablas_limpiar_legacy:
        try: db.table(t).delete().gt("id", 0).execute()
        except: pass
    for cedi in CEDIS:
        try: db.table("inventario").update({"stock": 0, "updated_at": datetime.now().isoformat()}).eq("cedi", cedi).execute()
        except: pass

# ══════════════════════════════════════════════════════
# IA NOVA
# ══════════════════════════════════════════════════════
def get_ia_key(provider):
    keys = {"gemini": ["GEMINI_API_KEY","GOOGLE_API_KEY"], "anthropic": ["ANTHROPIC_API_KEY"], "openai": ["OPENAI_API_KEY"]}
    for k in keys.get(provider, []):
        try:
            v = st.secrets.get(k, "")
            if v: return v
        except: pass
        v = os.getenv(k, "")
        if v: return v
    return ""

def build_context():
    inv_df = get_inv(); desp_df = get_desp(); lotes_df = get_lotes()
    veh_df = get_vehiculos(); rutas_df = get_rutas_db()
    cli_df = get_clientes(); alm_df = get_alm_clientes()
    stk = stock_total(inv_df); uso = round(stk / cfg("cap_almacen") * 100, 1) if cfg("cap_almacen") else 0
    fletes = int(desp_df["costo_flete"].sum()) if not desp_df.empty and "costo_flete" in desp_df.columns else 0
    tortas_t = int(desp_df["tortas"].sum()) if not desp_df.empty and "tortas" in desp_df.columns else 0
    veh_act = veh_df[veh_df["estado"] == "Activo"] if not veh_df.empty and "estado" in veh_df.columns else pd.DataFrame()
    n_cli = len(cli_df) if not cli_df.empty else 0
    n_alm = len(alm_df[alm_df["estado"] == "activo"]) if not alm_df.empty and "estado" in alm_df.columns else 0
    stk_cedi = {r["cedi"]: r["stock"] for _, r in inv_df.iterrows()} if not inv_df.empty and "cedi" in inv_df.columns else {}
    rutas_txt = []
    if not rutas_df.empty:
        for _, r in rutas_df.iterrows():
            if r.get("activa", True):
                fl = calcular_flete(r["km"], 1, True, True)
                rutas_txt.append(f"  - {r['municipio']}: {r['km']} km, flete noc: ${fl:,}")
    return f"""Eres NOVA, asistente IA de DistriNova ERP v10 — operador logístico integral (almacenamiento + transporte) en Norte de Antioquia, Colombia.
ESTADO ({datetime.now().strftime('%d/%m/%Y %H:%M')}):
- Stock CEDIs: {stk_cedi} | Total: {stk:,} uds ({uso}%)
- Clientes registrados: {n_cli} | Almacenamientos activos: {n_alm}
- Flota activa: {len(veh_act)} vehículos | Cap. 4 furgonetas: 672 tortas | Cap. 5 turbos: 5,000 tortas
- Ingresos fletes: ${fletes:,} | Tortas movilizadas: {tortas_t:,}
- Margen actual: {cfg('margen_pct')}% sobre factura total
TARIFAS: ${cfg('tarifa_km'):,}/km + {cfg('recargo_nocturno_pct')}% nocturno | Almacenamiento: ${cfg('tarifa_alm_ton_dia'):,}/ton/día
RUTAS ACTIVAS:\n{chr(10).join(rutas_txt) if rutas_txt else '  Sin rutas'}
EQUIPO: Yoany(COO), Gómez(Logística), Karen(Inventarios), Laura(Operaciones), Mafe(Documentación).
CADENA: Proveedores MP(Pereira) → CEDI Medellín → Fabricantes(Medellín) → Mayoristas(Medellín) → Minoristas(Pereira, 3 puntos)
Responde en español, usa **negrita** para valores clave, sé preciso y conciso."""

def call_nova(messages_hist, user_msg):
    gemini_key = get_ia_key("gemini")
    anthropic_key = get_ia_key("anthropic")
    openai_key = get_ia_key("openai")
    if not any([gemini_key, anthropic_key, openai_key]):
        return "**NOVA no configurada.** Agrega en `.streamlit/secrets.toml`:\n`GEMINI_API_KEY = \"AIza...\"` (gratis en aistudio.google.com)"
    system_ctx = build_context()
    if gemini_key:
        MODELS = ["gemini-2.5-flash-preview-04-17","gemini-1.5-flash-latest","gemini-1.5-flash","gemini-1.0-pro"]
        contents = [{"role":"user" if m["rol"]=="user" else "model","parts":[{"text":m["mensaje"]}]} for m in messages_hist[-12:]]
        contents.append({"role":"user","parts":[{"text":user_msg}]})
        last_err = ""
        for model in MODELS:
            try:
                resp = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}",
                    headers={"Content-Type":"application/json"},
                    json={"system_instruction":{"parts":[{"text":system_ctx}]},"contents":contents,"generationConfig":{"maxOutputTokens":1000,"temperature":0.4}},
                    timeout=30)
                if resp.status_code in [404,400]: last_err=f"{model} no disponible"; continue
                if resp.status_code == 429: last_err="cuota agotada"; continue
                if resp.status_code != 200: last_err=f"HTTP {resp.status_code}"; continue
                data = resp.json()
                if "candidates" in data and data["candidates"]:
                    parts = data["candidates"][0].get("content",{}).get("parts",[])
                    if parts: return parts[0]["text"]
                last_err = data.get("error",{}).get("message","sin candidatos")
            except Exception as e: last_err = str(e)
        return f"⚠️ Gemini no disponible ({last_err}). Verifica tu cuota en aistudio.google.com"
    if anthropic_key:
        try:
            msgs = [{"role":m["rol"],"content":m["mensaje"]} for m in messages_hist[-12:]]
            msgs.append({"role":"user","content":user_msg})
            resp = requests.post("https://api.anthropic.com/v1/messages",
                headers={"Content-Type":"application/json","x-api-key":anthropic_key,"anthropic-version":"2023-06-01"},
                json={"model":"claude-haiku-4-5-20251001","max_tokens":1000,"system":system_ctx,"messages":msgs},timeout=30)
            data = resp.json()
            if "content" in data and data["content"]: return data["content"][0]["text"]
        except Exception as e: return f"Error Claude: {e}"
    if openai_key:
        try:
            msgs = [{"role":"system","content":system_ctx}]+[{"role":m["rol"],"content":m["mensaje"]} for m in messages_hist[-12:]]
            msgs.append({"role":"user","content":user_msg})
            resp = requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Content-Type":"application/json","Authorization":f"Bearer {openai_key}"},
                json={"model":"gpt-4o-mini","max_tokens":1000,"temperature":0.4,"messages":msgs},timeout=30)
            data = resp.json()
            if "choices" in data: return data["choices"][0]["message"]["content"]
        except Exception as e: return f"Error OpenAI: {e}"
    return "Error desconocido en NOVA."

# ══════════════════════════════════════════════════════
# SESIÓN
# ══════════════════════════════════════════════════════
for k, v in [("modulo","WMS"),("subpag","Dashboard"),("usuario","Yoany"),("ia_msgs",[]),
             ("reset_paso1",False)]:
    if k not in st.session_state: st.session_state[k] = v

MODULOS = {
    "WMS": {"icon":"📦","full":"Almacén","tag":"tag-wms",
            "subs":[("📊","Dashboard","Panel"),("🏭","Inventario","Stock")]},
    "CLI": {"icon":"👥","full":"Clientes","tag":"tag-cli",
            "subs":[("👥","Directorio","Actores"),("📦","Stock Clientes","Almacenado"),("🍰","Perecederos","FIFO")]},
    "TMS": {"icon":"🚐","full":"Transporte","tag":"tag-tms",
            "subs":[("🗺️","Rutas","Planeador"),("🏙️","Gestión Rutas","Editar"),("📍","Mapa","Vista geo"),
                    ("📋","Órdenes Servicio","ODS"),("📝","Solicitudes Servicio","SS")]},
    "FIN": {"icon":"💵","full":"Finanzas","tag":"tag-fin",
            "subs":[("📈","Dashboard Financiero","Ingresos"),("💵","Cotizador","Tarifas"),("📊","P&G por Ruta","Rentabilidad"),("🧾","Documentos","Remisiones")]},
    "SYS": {"icon":"⚙️","full":"Sistema","tag":"tag-sys",
            "subs":[("🚐","Flota","Vehículos"),("🔧","Configuración","Parámetros"),("👥","Equipo","Roles")]},
    "IA":  {"icon":"🤖","full":"Asistente IA","tag":"tag-ia",
            "subs":[("🤖","Asistente","Chat"),("📈","Análisis","KPIs")]},
}
USUARIOS = {"Yoany":{"rol":"COO","icon":"👑"},"Gómez":{"rol":"Logística","icon":"🗺️"},
            "Karen":{"rol":"Inventarios","icon":"📦"},"Laura":{"rol":"Operaciones","icon":"🚛"},"Mafe":{"rol":"Documentación","icon":"🧾"}}

# ══════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════
with st.sidebar:
    now = datetime.now()
    st.markdown(f'<div class="dn-logo"><div class="dn-logo-title">DISTRI<span>NOVA</span></div><div class="dn-logo-sub">Operador Logístico · Norte Antioquia</div><div class="dn-badge">● v10.0 &nbsp;{now.strftime("%H:%M")}</div></div>', unsafe_allow_html=True)
    for mk, mod_ in MODULOS.items():
        st.markdown(f'<div class="dn-mod-hdr">{mod_["icon"]} &nbsp;{mod_["full"]}</div>', unsafe_allow_html=True)
        for si, sn, sd in mod_["subs"]:
            if st.button(f"{si}  {sn}", key=f"nav_{mk}_{sn}", use_container_width=True, help=sd):
                st.session_state.modulo = mk; st.session_state.subpag = sn
                st.session_state.reset_paso1 = False; st.rerun()
    st.divider()
    uk = st.selectbox("Usuario", list(USUARIOS.keys()),
                      index=list(USUARIOS.keys()).index(st.session_state.usuario),
                      key="usr_sel", label_visibility="collapsed")
    st.session_state.usuario = uk; ui = USUARIOS[uk]
    st.markdown(f'<div class="dn-user"><div class="dn-avatar">{ui["icon"]}</div><div><div class="dn-user-name">{uk}</div><div class="dn-user-role">{ui["rol"]}</div></div></div>', unsafe_allow_html=True)

mod = st.session_state.modulo; subpag = st.session_state.subpag
mod_info = MODULOS[mod]; usr_name = st.session_state.usuario

# ── Helpers UI ──────────────────────────────────────
def alerta(tipo, txt):
    cls = {"ok":"dn-ok","warn":"dn-warn","err":"dn-err","info":"dn-info","ia":"dn-ia"}
    ic  = {"ok":"●","warn":"▲","err":"✕","info":"ℹ","ia":"◈"}
    st.markdown(f'<div class="dn-alert {cls[tipo]}">{ic[tipo]}&nbsp; {txt}</div>', unsafe_allow_html=True)

def banner(titulo, sub, tag, label=""):
    st.markdown(f'<div class="dn-module-banner" data-label="{label}"><div class="dn-module-tag {tag}">{mod_info["icon"]} {mod_info["full"]}</div><div style="font-family:var(--cond);font-size:28px;font-weight:800;color:white;letter-spacing:.5px;margin-bottom:3px">{titulo}</div><div style="font-size:12px;color:var(--txt2)">{sub}</div></div>', unsafe_allow_html=True)

def mini_chart(labels, vals, color, height=190):
    fig = go.Figure(go.Bar(x=labels, y=vals, marker=dict(color=color, opacity=.85),
        text=[f"{v:,}" for v in vals], textposition="outside",
        textfont=dict(color="rgba(200,216,234,.7)", size=11)))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=22,b=4,l=4,r=4), height=height,
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#5A7A99")),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.04)", tickfont=dict(size=10, color="#5A7A99")))
    return fig

def gauge(val, mx, titulo):
    pct = val / mx if mx else 0
    c = "#00C97A" if pct < .6 else "#FFB800" if pct < .85 else "#FF4444"
    fig = go.Figure(go.Indicator(mode="gauge+number", value=val,
        title={"text":titulo,"font":{"color":"#5A7A99","size":10}},
        number={"font":{"color":"#C8D8EA","size":22,"family":"JetBrains Mono"}},
        gauge={"axis":{"range":[0,mx],"tickcolor":"#334D66","tickfont":{"size":8}},
               "bar":{"color":c,"thickness":.55},"bgcolor":"#16263D","bordercolor":"rgba(255,255,255,.07)",
               "steps":[{"range":[0,mx*.6],"color":"rgba(0,201,122,.04)"},{"range":[mx*.6,mx*.85],"color":"rgba(255,184,0,.04)"},{"range":[mx*.85,mx],"color":"rgba(255,68,68,.05)"}]}))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=36,b=8,l=16,r=16), height=175)
    return fig

def save_msg(rol, msg):
    st.session_state.ia_msgs.append({"rol":rol,"mensaje":msg,"ts":datetime.now().strftime("%H:%M")})
    try: supabase().table("ia_chat").insert({"usuario":usr_name,"rol":rol,"mensaje":msg}).execute()
    except: pass

def render_msg(msg):
    txt = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', msg.get("mensaje","")).replace("\n","<br>")
    if msg["rol"] == "user":
        st.markdown(f'<div class="ia-name-user">{usr_name}</div><div class="ia-bubble-user">{txt}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="ia-name-bot">◈ NOVA · {msg.get("ts","")}</div><div class="ia-bubble-bot">{txt}</div>', unsafe_allow_html=True)

def tipo_os_badge(tipo):
    labels = {"recoleccion":"🔴 Recolección","transferencia":"🔵 Transferencia","entrega_cedi":"🟠 Entrega CEDI","entrega_directa":"🟢 Entrega Directa"}
    return labels.get(tipo, tipo)

# ══════════════════════════════════════════════════════════════════
# PÁGINAS
# ══════════════════════════════════════════════════════════════════

# ── WMS Dashboard ──────────────────────────────────────────────
if mod == "WMS" and subpag == "Dashboard":
    banner("Panel de Control","Operación en tiempo real · Norte de Antioquia","tag-wms","WMS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    inv_df = get_inv(); desp_df = get_desp(); lotes_df = get_lotes()
    cli_df = get_clientes(); alm_df = get_alm_clientes()
    stk = stock_total(inv_df); uso = round(stk / cfg("cap_almacen") * 100, 1) if cfg("cap_almacen") else 0
    fletes = int(desp_df["costo_flete"].sum()) if not desp_df.empty and "costo_flete" in desp_df.columns else 0
    tortas_t = int(desp_df["tortas"].sum()) if not desp_df.empty and "tortas" in desp_df.columns else 0
    n_cli = len(cli_df) if not cli_df.empty else 0
    alm_act = alm_df[alm_df["estado"]=="activo"] if not alm_df.empty and "estado" in alm_df.columns else pd.DataFrame()
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Stock Total",f"{stk:,}",f"{uso}% almacén")
    k2.metric("Clientes",n_cli)
    k3.metric("Ingresos Fletes",f"${fletes:,}")
    k4.metric("Tortas Movilizadas",f"{tortas_t:,}")
    k5,k6,k7,k8 = st.columns(4)
    k5.metric("Cap. Almacén",f"{cfg('cap_almacen'):,}",f"{cfg('cap_almacen')-stk:,} libres")
    k6.metric("Almacenamientos Activos",len(alm_act))
    k7.metric("Furgonetas Activas","4")
    k8.metric("Turbos Disponibles","3 activos")
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    alts = []
    if inv_df.empty or "cedi" not in inv_df.columns:
        alts.append(("warn","Tabla inventario vacía. Ejecuta el SQL inicial en Supabase."))
    else:
        for _, row in inv_df.iterrows():
            s = row["stock"]
            if s <= cfg("stock_min"): alts.append(("err",f"<b>RUPTURA CEDI {row['cedi']}:</b> {s} uds."))
            elif s <= cfg("stock_min")*2: alts.append(("warn",f"Stock bajo CEDI {row['cedi']}: {s} uds."))
    if uso > 85: alts.append(("err",f"Almacén al {uso}%."))
    elif uso > 65: alts.append(("warn",f"Almacén al {uso}%."))
    if not lotes_df.empty and "fecha_vencimiento" in lotes_df.columns:
        hoy = date.today(); lotes_df["fv"] = pd.to_datetime(lotes_df["fecha_vencimiento"]).dt.date
        for _, l in lotes_df.iterrows():
            dias = (l["fv"]-hoy).days
            if dias <= cfg("alerta_vence_dias"):
                alts.append(("err" if dias<=0 else "warn",f"Lote {l.get('lote_id','?')} ({l.get('cedi','?')}): {l.get('cantidad',0)} uds {'VENCIDAS' if dias<0 else 'hoy' if dias==0 else f'vencen en {dias}d'}."))
    if not alts: alts.append(("ok","Todos los indicadores dentro de parámetros normales."))
    ca, cb = st.columns([3,2])
    with ca:
        st.markdown('<div class="dn-section"><div class="dn-section-header">ALERTAS OPERATIVAS</div><div class="dn-section-body">', unsafe_allow_html=True)
        for t, tx in alts: alerta(t, tx)
        st.markdown('</div></div>', unsafe_allow_html=True)
    with cb: st.plotly_chart(gauge(stk, cfg("cap_almacen"), f"ALMACÉN {uso}%"), use_container_width=True)
    gc1, gc2 = st.columns(2)
    with gc1:
        st.markdown('<div class="dn-section"><div class="dn-section-header">STOCK POR CEDI</div><div class="dn-section-body">', unsafe_allow_html=True)
        if not inv_df.empty and "cedi" in inv_df.columns:
            st.plotly_chart(mini_chart(inv_df["cedi"].tolist(), inv_df["stock"].tolist(), "#1E88E5"), use_container_width=True)
        else: st.caption("Sin datos.")
        st.markdown('</div></div>', unsafe_allow_html=True)
    with gc2:
        st.markdown('<div class="dn-section"><div class="dn-section-header">CLIENTES POR TIPO</div><div class="dn-section-body">', unsafe_allow_html=True)
        if not cli_df.empty and "tipo" in cli_df.columns:
            grp = cli_df.groupby("tipo").size().reset_index(name="count")
            fig = px.pie(grp, values="count", names="tipo", color_discrete_sequence=["#FF4444","#FF8C00","#1E88E5","#00C97A"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#5A7A99"), height=190, margin=dict(t=10,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
        else: alerta("info","Sin clientes registrados. Ve a Clientes → Directorio.")
        st.markdown('</div></div>', unsafe_allow_html=True)
    cc1,cc2,cc3 = st.columns(3)
    for col, nom, rol_ in [(cc1,"Medellín","Principal"),(cc2,"Santa Rosa","Distribución"),(cc3,"Taraza","Distribución")]:
        sk = stock_cedi(inv_df, nom); pct = min(1.0, sk/(cfg("stock_min")*4)) if cfg("stock_min")>0 else 0
        est = "err" if sk<=cfg("stock_min") else "warn" if sk<=cfg("stock_min")*2 else "ok"
        lbl = "CRÍTICO" if est=="err" else "BAJO" if est=="warn" else "NORMAL"
        ec = f"status-{est}"; bc = "#FF4444" if est=="err" else "#FFB800" if est=="warn" else "#00C97A"
        with col:
            st.markdown(f'<div class="dn-cedi"><div class="dn-cedi-tag">CEDI · {rol_}</div><div class="dn-cedi-name">{nom}</div><div style="margin-top:5px"><span class="dn-status {ec}">{lbl}</span></div><div class="dn-cedi-stock">{sk:,}</div><div style="font-size:10px;color:var(--txt3)">unidades en stock</div><div class="dn-cedi-bar"><div class="dn-cedi-fill" style="width:{pct*100:.0f}%;background:{bc}"></div></div><div style="display:flex;justify-content:space-between;font-size:10px;color:var(--txt3);margin-top:5px"><span>Mín:{cfg("stock_min")}</span><span>Cap:{cfg("cap_almacen"):,}</span></div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if not alm_act.empty:
        st.markdown('<div class="dn-section"><div class="dn-section-header"><span>ALMACENAMIENTOS ACTIVOS</span></div><div class="dn-section-body">', unsafe_allow_html=True)
        ok = [c for c in ["cliente_nombre","tipo_actor","material","cantidad","unidad","peso_ton","fecha_ingreso","cedi","estado"] if c in alm_act.columns]
        st.dataframe(alm_act[ok].head(6), use_container_width=True, hide_index=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    if st.button("↺ Actualizar"): st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── WMS Inventario ─────────────────────────────────────────────
elif mod == "WMS" and subpag == "Inventario":
    banner("Inventario CEDI","Control de stock · Responsable: Karen","tag-wms","WMS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    inv_df = get_inv(); stk = stock_total(inv_df); uso = stk/cfg("cap_almacen")*100 if cfg("cap_almacen") else 0
    cg, ci = st.columns([1,2])
    with cg:
        st.plotly_chart(gauge(stk, cfg("cap_almacen"),"USO ALMACÉN"), use_container_width=True)
        alerta("info" if uso<65 else "warn" if uso<85 else "err",f"Al <b>{uso:.1f}%</b> — {cfg('cap_almacen')-stk:,} libres")
    with ci:
        c1,c2,c3 = st.columns(3)
        for col, nom in [(c1,"Medellín"),(c2,"Santa Rosa"),(c3,"Taraza")]:
            sk = stock_cedi(inv_df, nom)
            est = "🔴" if sk<=cfg("stock_min") else "🟡" if sk<=cfg("stock_min")*2 else "🟢"
            col.metric(f"{est} {nom}", f"{sk:,}", f"Mín:{cfg('stock_min')}")
            col.progress(min(1.0, sk/(cfg("stock_min")*4)) if cfg("stock_min")>0 else 0)
    st.divider()
    f1, f2 = st.columns(2)
    with f1:
        st.markdown('<div class="dn-form"><div class="dn-form-title">REGISTRAR MOVIMIENTO MANUAL</div>', unsafe_allow_html=True)
        cs = st.selectbox("CEDI", CEDIS, key="inv_cedi")
        ts = st.selectbox("Tipo", ["entrada","salida","ajuste"], key="inv_tipo")
        qs = st.number_input("Cantidad", 1, 99999999, key="inv_qty")
        ds = st.text_input("Documento", placeholder="OC-2026-001", key="inv_doc")
        if st.button("Registrar", use_container_width=True):
            sk2 = stock_cedi(inv_df, cs)
            if ts=="salida" and sk2<qs: alerta("err",f"Stock insuficiente: {sk2}")
            # cap sin límite — sin bloqueo por capacidad
            else:
                nv = sk2+qs if ts=="entrada" else sk2-qs if ts=="salida" else qs
                try:
                    db = supabase()
                    db.table("inventario").update({"stock":nv,"updated_at":datetime.now().isoformat()}).eq("cedi",cs).execute()
                    db.table("movimientos").insert({"cedi":cs,"tipo":ts,"cantidad":qs,"documento":ds or "Sin doc","stock_result":nv,"usuario":usr_name}).execute()
                    alerta("ok",f"{cs}: {sk2} → <b>{nv}</b>"); st.rerun()
                except Exception as e: alerta("err",f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    with f2:
        mv = get_mov()
        st.markdown('<div class="dn-section"><div class="dn-section-header">BITÁCORA</div><div class="dn-section-body">', unsafe_allow_html=True)
        if not mv.empty:
            ok = [c for c in ["created_at","cedi","tipo","cantidad","documento","stock_result"] if c in mv.columns]
            st.dataframe(mv[ok], use_container_width=True, hide_index=True, height=300)
        else: alerta("info","Sin movimientos registrados.")
        st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── WMS Perecederos (redirige a CLI) ──────────────────────────
elif mod == "WMS" and subpag == "Perecederos":
    st.session_state.modulo = "CLI"; st.session_state.subpag = "Perecederos"; st.rerun()

# ══════════════════════════════════════════════════════
# CLIENTES — Directorio
# ══════════════════════════════════════════════════════
elif mod == "CLI" and subpag == "Directorio":
    banner("Directorio de Clientes","Proveedores · Fabricantes · Mayoristas · Minoristas","tag-cli","CLI")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    cli_df = get_clientes()
    t_prov,t_fab,t_may,t_min,t_add = st.tabs(["🏭  PROVEEDORES","🏗️  FABRICANTES","🏢  MAYORISTAS","🏪  MINORISTAS","➕  AGREGAR"])
    TIPO_CIUDADES = {"proveedor":"Pereira","fabricante":"Medellín","mayorista":"Medellín","minorista":"Pereira"}
    def render_clientes_tab(tipo, cli_df):
        sub = cli_df[cli_df["tipo"]==tipo] if not cli_df.empty and "tipo" in cli_df.columns else pd.DataFrame()
        if sub.empty:
            alerta("info",f"Sin {tipo}s registrados. Ve a ➕ Agregar.")
            return
        for _,c in sub.iterrows():
            color = TIPO_COLOR.get(tipo,"blue")
            st.markdown(f'''<div class="cli-card">
                <div class="cli-tipo" style="color:{{"proveedor":"#FF4444","fabricante":"#FF8C00","mayorista":"#1E88E5","minorista":"#00C97A"}}.get("{tipo}","#fff")">
                {tipo.upper()} · {c.get("ciudad","—")}</div>
                <div class="cli-nombre">{c.get("nombre","Sin nombre")}</div>
                <div class="cli-info">📍 {c.get("direccion","Sin dirección")} &nbsp;|&nbsp; 📞 {c.get("contacto","—")} &nbsp;|&nbsp; 🏭 CEDI: {c.get("cedi_asignado","Sin asignar")}</div>
                {"<div class='cli-info'>📝 "+str(c.get("notas",""))+"</div>" if c.get("notas") else ""}
            </div>''', unsafe_allow_html=True)
        # Editar cliente
        st.markdown("---")
        st.markdown(f"**✏️ Editar {tipo}:**")
        nombres = sub["nombre"].tolist() if "nombre" in sub.columns else []
        if nombres:
            sel_nom = st.selectbox("Seleccionar", nombres, key=f"ed_nom_{tipo}")
            sel_row = sub[sub["nombre"]==sel_nom].iloc[0]
            c1,c2,c3 = st.columns(3)
            with c1:
                nn = st.text_input("Nombre",str(sel_row.get("nombre","")),key=f"ed_n_{tipo}")
                nc = st.text_input("Ciudad",str(sel_row.get("ciudad",TIPO_CIUDADES.get(tipo,""))),key=f"ed_c_{tipo}")
            with c2:
                nd = st.text_input("Dirección",str(sel_row.get("direccion","")),key=f"ed_d_{tipo}")
                nct = st.text_input("Contacto",str(sel_row.get("contacto","")),key=f"ed_ct_{tipo}")
            with c3:
                nca = st.selectbox("CEDI Asignado",["Sin asignar"]+CEDIS,
                    index=(["Sin asignar"]+CEDIS).index(sel_row.get("cedi_asignado","Sin asignar")) if sel_row.get("cedi_asignado","Sin asignar") in ["Sin asignar"]+CEDIS else 0,
                    key=f"ed_ca_{tipo}")
                nno = st.text_input("Notas",str(sel_row.get("notas","")),key=f"ed_no_{tipo}")
            col_save,col_del = st.columns(2)
            with col_save:
                if st.button("💾 Guardar",key=f"ed_save_{tipo}",use_container_width=True):
                    try:
                        supabase().table("clientes").update({"nombre":nn,"ciudad":nc,"direccion":nd,"contacto":nct,"cedi_asignado":nca,"notas":nno}).eq("id",int(sel_row["id"])).execute()
                        alerta("ok","Cliente actualizado."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
            with col_del:
                if st.button("🗑️ Eliminar",key=f"ed_del_{tipo}",use_container_width=True):
                    try:
                        supabase().table("clientes").delete().eq("id",int(sel_row["id"])).execute()
                        alerta("ok","Cliente eliminado."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")

    with t_prov:
        alerta("info","<b>Proveedores</b> — Suministran materias primas (Pereira). DistriNova almacena su MP y la transporta al fabricante cuando se vende.")
        render_clientes_tab("proveedor", cli_df)
    with t_fab:
        alerta("info","<b>Fabricantes</b> — Producen las tortas (Medellín). DistriNova almacena su producto terminado y lo distribuye.")
        render_clientes_tab("fabricante", cli_df)
    with t_may:
        alerta("info","<b>Mayoristas</b> — Distribuidores en Medellín. Reciben producto del fabricante y distribuyen a minoristas.")
        render_clientes_tab("mayorista", cli_df)
    with t_min:
        alerta("info","<b>Minoristas</b> — En Pereira, con 3 puntos de venta. DistriNova entrega en sus puntos.")
        render_clientes_tab("minorista", cli_df)
    with t_add:
        st.markdown('<div class="dn-form"><div class="dn-form-title">REGISTRAR NUEVO CLIENTE</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            a_tipo = st.selectbox("Tipo de actor",["proveedor","fabricante","mayorista","minorista"],key="a_tipo")
            a_nombre = st.text_input("Nombre / Razón social",key="a_nombre")
            a_ciudad = st.text_input("Ciudad",value=TIPO_CIUDADES.get(st.session_state.get("a_tipo","proveedor"),"Medellín"),key="a_ciudad")
            a_dir = st.text_input("Dirección",key="a_dir")
        with c2:
            a_contacto = st.text_input("Contacto / Nombre representante",key="a_contacto")
            a_tel = st.text_input("Teléfono",key="a_tel")
            a_cedi = st.selectbox("CEDI Asignado",["Sin asignar"]+CEDIS,key="a_cedi")
            a_notas = st.text_area("Notas / Descripción",height=68,key="a_notas")
        if st.button("➕ Registrar Cliente",use_container_width=True):
            if not a_nombre: alerta("err","Ingresa el nombre del cliente.")
            else:
                try:
                    supabase().table("clientes").insert({
                        "nombre":a_nombre.strip(),"tipo":a_tipo,"ciudad":a_ciudad,"direccion":a_dir,
                        "contacto":a_contacto,"telefono":a_tel,"cedi_asignado":a_cedi,
                        "notas":a_notas,"activo":True
                    }).execute()
                    alerta("ok",f"<b>{a_nombre}</b> ({a_tipo}) registrado correctamente."); st.rerun()
                except Exception as e: alerta("err",f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── CLIENTES — Stock Clientes ──────────────────────────────────
elif mod == "CLI" and subpag == "Stock Clientes":
    banner("Stock por Cliente","Lo que DistriNova almacena para cada actor de la cadena","tag-cli","ALM")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alm_df = get_alm_clientes(); cli_df = get_clientes()
    cli_list = cli_df["nombre"].tolist() if not cli_df.empty and "nombre" in cli_df.columns else []
    t1,t2 = st.tabs(["📋  ALMACENAMIENTOS ACTIVOS","➕  REGISTRAR ENTRADA"])
    with t1:
        if alm_df.empty:
            alerta("info","Sin registros de almacenamiento. Registra una entrada para comenzar.")
        else:
            hoy = date.today()
            # Compute dias and cost
            filas = []
            for _,r in alm_df.iterrows():
                fi_str = str(r.get("fecha_ingreso",""))[:10]
                fs_str = str(r.get("fecha_salida",""))[:10] if r.get("fecha_salida") else None
                d = dias_almacenado(fi_str, fs_str)
                pt = float(r.get("peso_ton",0))
                costo = costo_almacenamiento(pt, d)
                filas.append({**r.to_dict(),"dias_calculados":d,"costo_acumulado_calc":costo})
            df_show = pd.DataFrame(filas)
            # Filters
            col_f1,col_f2 = st.columns(2)
            with col_f1:
                f_estado = st.selectbox("Estado",["Todos","activo","despachado","retirado"],key="alm_f_est")
            with col_f2:
                f_tipo = st.selectbox("Tipo actor",["Todos","proveedor","fabricante","mayorista","minorista"],key="alm_f_tipo")
            if f_estado != "Todos" and "estado" in df_show.columns:
                df_show = df_show[df_show["estado"]==f_estado]
            if f_tipo != "Todos" and "tipo_actor" in df_show.columns:
                df_show = df_show[df_show["tipo_actor"]==f_tipo]
            # Metrics
            tot_costo = df_show["costo_acumulado_calc"].sum() if "costo_acumulado_calc" in df_show.columns else 0
            tot_ton = df_show["peso_ton"].sum() if "peso_ton" in df_show.columns else 0
            k1,k2,k3 = st.columns(3)
            k1.metric("Registros",len(df_show))
            k2.metric("Toneladas almacenadas",f"{tot_ton:.2f} T")
            k3.metric("Costo acumulado total",f"${tot_costo:,.0f}")
            ok_cols = [c for c in ["cliente_nombre","tipo_actor","material","cantidad","unidad","peso_ton","fecha_ingreso","fecha_salida","dias_calculados","costo_acumulado_calc","cedi","estado"] if c in df_show.columns]
            st.dataframe(df_show[ok_cols], use_container_width=True, hide_index=True)
            # Close storage
            st.markdown("---")
            st.markdown("**🔒 Cerrar almacenamiento (marcar como despachado):**")
            activos = df_show[df_show["estado"]=="activo"] if "estado" in df_show.columns else pd.DataFrame()
            if not activos.empty and "id" in activos.columns:
                id_sel = st.selectbox("ID a cerrar", activos["id"].tolist(), key="alm_close_id")
                row_sel = activos[activos["id"]==id_sel].iloc[0]
                st.caption(f"Cliente: {row_sel.get('cliente_nombre','—')} | Material: {row_sel.get('material','—')} | Días: {row_sel.get('dias_calculados',0)} | Costo: ${row_sel.get('costo_acumulado_calc',0):,.0f}")
                if st.button("✅ Marcar como Despachado",key="alm_close_btn"):
                    try:
                        supabase().table("almacenamiento_clientes").update({"estado":"despachado","fecha_salida":date.today().isoformat()}).eq("id",int(id_sel)).execute()
                        alerta("ok","Almacenamiento cerrado correctamente."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
    with t2:
        st.markdown('<div class="dn-form"><div class="dn-form-title">REGISTRAR ENTRADA DE ALMACENAMIENTO</div>', unsafe_allow_html=True)
        alerta("info","Registra aquí lo que DistriNova recibe para almacenar. El costo se calcula automáticamente por día.")
        c1,c2 = st.columns(2)
        with c1:
            if cli_list:
                a_cli = st.selectbox("Cliente",cli_list,key="a2_cli")
                cli_row = cli_df[cli_df["nombre"]==a_cli].iloc[0] if not cli_df.empty else {}
                a_tipo_act = str(cli_row.get("tipo","—")) if len(cli_row) else "—"
                a_cedi_sugerido = str(cli_row.get("cedi_asignado","Medellín")) if len(cli_row) else "Medellín"
                st.caption(f"Tipo: **{a_tipo_act}** | CEDI asignado: {a_cedi_sugerido}")
            else:
                alerta("warn","Primero registra clientes en Clientes → Directorio.")
                a_cli = st.text_input("Cliente (manual)",key="a2_cli_m")
                a_tipo_act = "proveedor"; a_cedi_sugerido = "Medellín"
            a_material = st.text_input("Material / Producto",placeholder="Harina, Tortas, Azúcar...",key="a2_mat")
            a_cantidad  = st.number_input("Cantidad",0.0,value=100.0,step=1.0,key="a2_qty")
            a_unidad    = st.selectbox("Unidad",["kg","ton","unidades","L","cajas","sacos"],key="a2_uni")
        with c2:
            a_cedi_alm  = st.selectbox("CEDI donde se almacena",CEDIS,
                index=CEDIS.index(a_cedi_sugerido) if a_cedi_sugerido in CEDIS else 0,key="a2_cedi")
            a_fi        = st.date_input("Fecha ingreso",value=date.today(),key="a2_fi")
            a_notas_alm = st.text_input("Notas (opcional)",key="a2_notas")
            # Auto-calculate peso_ton
            if a_unidad == "ton": a_peso_ton = float(a_cantidad)
            elif a_unidad == "kg": a_peso_ton = float(a_cantidad)/1000.0
            elif a_unidad == "sacos": a_peso_ton = float(a_cantidad)*0.05  # 50kg por saco
            else: a_peso_ton = float(a_cantidad)/1000.0  # estimado genérico
            st.metric("Peso estimado",f"{a_peso_ton:.3f} ton")
        costo_30d = costo_almacenamiento(a_peso_ton, 30)
        costo_7d  = costo_almacenamiento(a_peso_ton, 7)
        alerta("info",f"Costo estimado: <b>${costo_7d:,} (7 días)</b> · <b>${costo_30d:,} (30 días)</b> · Tarifa: ${cfg('tarifa_alm_ton_dia'):,}/ton/día")
        if st.button("📥 Registrar Entrada",use_container_width=True):
            if not a_material: alerta("err","Especifica el material.")
            elif a_cantidad <= 0: alerta("err","Cantidad debe ser mayor a 0.")
            else:
                try:
                    cli_id = int(cli_df[cli_df["nombre"]==a_cli]["id"].values[0]) if cli_list and not cli_df.empty else None
                    supabase().table("almacenamiento_clientes").insert({
                        "cliente_id":cli_id,"cliente_nombre":a_cli,"tipo_actor":a_tipo_act,
                        "material":a_material,"cantidad":float(a_cantidad),"unidad":a_unidad,
                        "peso_ton":float(a_peso_ton),"fecha_ingreso":a_fi.isoformat(),
                        "tarifa_ton_dia":cfg("tarifa_alm_ton_dia"),"cedi":a_cedi_alm,
                        "estado":"activo","notas":a_notas_alm,"usuario":usr_name
                    }).execute()
                    alerta("ok",f"✅ <b>{a_material}</b> ({a_cantidad} {a_unidad}) de <b>{a_cli}</b> → CEDI {a_cedi_alm}. Costo acumulando desde hoy."); st.rerun()
                except Exception as e: alerta("err",f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── CLI Perecederos ────────────────────────────────────────────
elif mod == "CLI" and subpag == "Perecederos":
    banner("Perecederos por Cliente",f"FIFO · Vida útil: {cfg('vida_util_dias')} días · Integrado con almacenamiento","tag-cli","FIFO")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alerta("info",f"<b>FIFO activo.</b> Vida útil tortas: <b>{cfg('vida_util_dias')} días</b>. Alerta anticipada: {cfg('alerta_vence_dias')} días.")
    t1,t2 = st.tabs(["📋  LOTES ACTIVOS","➕  REGISTRAR LOTE"])
    with t1:
        lotes_df = get_lotes()
        if not lotes_df.empty and "fecha_vencimiento" in lotes_df.columns:
            hoy = date.today(); lotes_df["fv"] = pd.to_datetime(lotes_df["fecha_vencimiento"]).dt.date
            lotes_df["dias"] = lotes_df["fv"].apply(lambda x: (x-hoy).days)
            venc_hoy = lotes_df[lotes_df["dias"]<=0]
            venc_prox = lotes_df[(lotes_df["dias"]>0)&(lotes_df["dias"]<=cfg("alerta_vence_dias"))]
            if not venc_hoy.empty: alerta("err",f"⚠️ <b>{len(venc_hoy)} lote(s) VENCIDOS o vencen HOY.</b> Revisar y retirar.")
            if not venc_prox.empty: alerta("warn",f"🟡 <b>{len(venc_prox)} lote(s)</b> vencen en los próximos {cfg('alerta_vence_dias')} días.")
            k1,k2,k3 = st.columns(3)
            k1.metric("Total lotes activos", len(lotes_df[lotes_df.get("estado","activo")!="inactivo"] if "estado" in lotes_df.columns else lotes_df))
            k2.metric("Lotes con alerta", len(venc_hoy)+len(venc_prox))
            k3.metric("Unidades en lotes", int(lotes_df["cantidad"].sum()) if "cantidad" in lotes_df.columns else 0)
            ok_ = [c for c in ["lote_id","cedi","cantidad","fecha_ingreso","fecha_vencimiento","dias","proveedor","estado"] if c in lotes_df.columns]
            st.dataframe(lotes_df[ok_].sort_values("dias"), use_container_width=True, hide_index=True)
        else: alerta("info","Sin lotes registrados. Usa ➕ Registrar Lote para añadir uno.")
    with t2:
        st.markdown('<div class="dn-form"><div class="dn-form-title">REGISTRAR LOTE PERECEDERO</div>', unsafe_allow_html=True)
        alerta("info","Registra aquí los lotes de tortas u otros perecederos para control FIFO automático.")
        c1,c2 = st.columns(2)
        with c1:
            ced_l = st.selectbox("CEDI donde está el lote",CEDIS,key="lc")
            qty_l = st.number_input("Cantidad (unidades/kg)",1,99999999,100,key="lq")
            prov  = st.text_input("Fabricante / Proveedor",placeholder="LogiCakes, Sabora...",key="lp")
        with c2:
            fi  = st.date_input("Fecha ingreso",value=date.today(),key="lfi")
            fv_ = st.date_input("Fecha vencimiento",value=date.today()+timedelta(days=cfg("vida_util_dias")),key="lfv")
            lid = st.text_input("ID Lote (autosugerido)",value=f"LOTE-{date.today().strftime('%Y%m%d')}-{ced_l[:3].upper()}",key="lid")
        vida = (fv_-fi).days
        if vida > 0: alerta("ok",f"Vida útil del lote: <b>{vida} días</b>")
        else: alerta("err","⚠️ La fecha de vencimiento debe ser posterior al ingreso.")
        if st.button("🍰 Registrar Lote",use_container_width=True):
            if not lid: alerta("err","El ID del lote es requerido.")
            elif vida <= 0: alerta("err","Corrige las fechas primero.")
            else:
                try:
                    supabase().table("lotes").insert({"lote_id":lid,"cedi":ced_l,"cantidad":qty_l,"fecha_ingreso":fi.isoformat(),"fecha_vencimiento":fv_.isoformat(),"proveedor":prov,"estado":"activo"}).execute()
                    alerta("ok",f"✅ Lote <b>{lid}</b> registrado en CEDI {ced_l}."); st.rerun()
                except Exception as e: alerta("err",f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS Rutas ──────────────────────────────────────────────────
elif mod == "TMS" and subpag == "Rutas":
    banner("Planeador de Rutas","Entregas antes de las 5:00 A.M. · Responsable: Gómez","tag-tms","TMS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alerta("warn","⏰ Todas las entregas deben llegar <b>antes de las 5:00 A.M.</b>")
    rutas_df = get_rutas_db(); veh_df = get_vehiculos(); inv_df = get_inv()
    activas = rutas_df[rutas_df["activa"]==True] if "activa" in rutas_df.columns else rutas_df
    veh_act = veh_df[veh_df["estado"]=="Activo"] if not veh_df.empty and "estado" in veh_df.columns else pd.DataFrame()
    cf, cr = st.columns(2)
    with cf:
        st.markdown('<div class="dn-form"><div class="dn-form-title">CONFIGURAR DESPACHO</div>', unsafe_allow_html=True)
        mun = st.selectbox("Municipio",activas["municipio"].tolist(),key="r_mun")
        row_r = activas[activas["municipio"]==mun].iloc[0]
        qty = st.number_input("Unidades a transportar",1,10000,168,key="r_qty")
        if not veh_act.empty:
            v_sel = st.selectbox("Vehículo",veh_act["codigo"].tolist(),key="r_veh")
            rv = veh_act[veh_act["codigo"]==v_sel].iloc[0]; cap_v = int(rv["capacidad"])
        else: v_sel="FRG-01"; cap_v=168
        hora = st.time_input("Hora de salida",key="r_hora")
        noc = st.checkbox(f"Jornada Nocturna (+{cfg('recargo_nocturno_pct')}%)",value=True,key="r_noc")
        ida = st.checkbox("Incluir regreso vacío",value=True,key="r_ida")
        reg = st.button("Registrar Despacho",use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    km = float(row_r["km"]); furgs = math.ceil(qty/cap_v)
    flete = calcular_flete(km,furgs,noc,ida)
    margen_os,total_con_margen = aplicar_margen(flete)
    sal = str(row_r.get("salida_max","03:00")); sh,sm = sal.split(":")
    hora_ok = hora.hour<int(sh) or (hora.hour==int(sh) and hora.minute<=int(sm))
    with cr:
        st.markdown('<div class="dn-section"><div class="dn-section-header">TRAZABILIDAD</div><div class="dn-section-body">', unsafe_allow_html=True)
        alerta("ok","Horario factible ✓") if hora_ok else alerta("err",f"No llegas a tiempo. Máxima: {sal} AM.")
        stk_mde = stock_cedi(inv_df,"Medellín")
        if stk_mde<qty: alerta("err",f"Stock insuficiente CEDI Medellín: {stk_mde} uds.")
        km_total = km*2 if ida else km
        st.dataframe(pd.DataFrame({"Campo":["Ruta","Distancia","Vehículos","Unidades","Jornada","Flete base",f"Margen {cfg('margen_pct')}%","Total a facturar","Salida máx."],
            "Valor":[f"Medellín→{mun}",f"{km_total:.1f}km",f"{furgs}x {v_sel}",f"{qty:,}","Nocturna" if noc else "Diurna",f"${flete:,}",f"${margen_os:,}",f"${total_con_margen:,}",f"{sal} AM"]}),
            use_container_width=True,hide_index=True)
        kc1,kc2,kc3 = st.columns(3)
        kc1.metric("Vehículos",furgs); kc2.metric("Flete base",f"${flete:,}"); kc3.metric("Total c/margen",f"${total_con_margen:,}")
        st.markdown('</div></div>', unsafe_allow_html=True)
    if reg:
        stk_mde = stock_cedi(get_inv(),"Medellín")
        if stk_mde<qty: alerta("err","Stock insuficiente.")
        else:
            try:
                db = supabase(); num = f"REM-{1001+len(get_desp())}"
                db.table("inventario").update({"stock":stk_mde-qty,"updated_at":datetime.now().isoformat()}).eq("cedi","Medellín").execute()
                db.table("despachos").insert({"remision":num,"cedi_origen":"Medellín","destino":mun,"km":km_total,"tortas":qty,"furgonetas":furgs,"nocturno":noc,"costo_flete":flete,"usuario":usr_name}).execute()
                db.table("movimientos").insert({"cedi":"Medellín","tipo":"salida","cantidad":qty,"documento":num,"stock_result":stk_mde-qty,"usuario":usr_name}).execute()
                alerta("ok",f"<b>{num}</b> — {qty} uds → {mun} — Flete: <b>${flete:,}</b> | Total: <b>${total_con_margen:,}</b>"); st.balloons()
            except Exception as e: alerta("err",f"Error: {e}")
    st.divider()
    st.markdown('<div class="dn-section"><div class="dn-section-header">TABLA MAESTRA DE RUTAS — 1 vehículo, ida y vuelta</div><div class="dn-section-body">', unsafe_allow_html=True)
    tabla = []
    for _,r in activas.iterrows():
        cd = calcular_flete(r["km"],1,False,True); cn = calcular_flete(r["km"],1,True,True)
        _,cd_m = aplicar_margen(cd); _,cn_m = aplicar_margen(cn)
        tabla.append({"Municipio":r["municipio"],"KM 1 vía":r["km"],"KM i/v":float(r["km"])*2,
                      "Flete diurno":f"${cd:,}",f"+ Margen {cfg('margen_pct')}%":f"${cd_m:,}",
                      "Flete nocturno":f"${cn:,}","Total noc c/margen":f"${cn_m:,}","Salida máx.":r.get("salida_max","—")})
    st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)
    alerta("info","<b>Fórmula:</b> km×2 (i/v) × tarifa/km × vehículos × (1+recargo%) × (1+margen%)")
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS Gestión Rutas ─────────────────────────────────────────
elif mod == "TMS" and subpag == "Gestión Rutas":
    banner("Gestión de Rutas","Editar KMs — actualización automática de fletes","tag-tms","RUTAS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alerta("info","✏️ Modificar los <b>KM</b> de cualquier ruta actualiza automáticamente <b>todos los fletes, cotizaciones y P&G</b> del sistema.")
    t1,t2 = st.tabs(["🗺️  RUTAS REGISTRADAS","➕  AGREGAR RUTA"])
    with t1:
        rutas_df = get_rutas_db()
        if not rutas_df.empty:
            ok = [c for c in ["municipio","km","tiempo_est","salida_max","lat","lon","activa"] if c in rutas_df.columns]
            st.dataframe(rutas_df[ok], use_container_width=True, hide_index=True)
            st.subheader("✏️ Editar ruta")
            mun_ed = st.selectbox("Municipio a editar",rutas_df["municipio"].tolist(),key="red_mun")
            re_ = rutas_df[rutas_df["municipio"]==mun_ed].iloc[0]
            c1,c2,c3 = st.columns(3)
            with c1:
                nkm = st.number_input("KM desde Medellín",0.0,2000.0,float(re_["km"]),step=0.1,key="red_km")
                ntpo = st.text_input("Tiempo est.",str(re_.get("tiempo_est","—")),key="red_tpo")
            with c2:
                nsal = st.text_input("Salida máx. (HH:MM)",str(re_.get("salida_max","03:00")),key="red_sal")
                nlat = st.number_input("Latitud",-90.0,90.0,float(re_.get("lat",7.0)),step=0.0001,format="%.4f",key="red_lat")
            with c3:
                nlon = st.number_input("Longitud",-180.0,0.0,float(re_.get("lon",-75.5)),step=0.0001,format="%.4f",key="red_lon")
                nact = st.checkbox("Activa",bool(re_.get("activa",True)),key="red_act")
            # Live preview cuando cambia km
            if nkm != float(re_["km"]):
                cd_new = calcular_flete(nkm,1,False,True); cn_new = calcular_flete(nkm,1,True,True)
                _,cd_m = aplicar_margen(cd_new); _,cn_m = aplicar_margen(cn_new)
                alerta("info",f"<b>Vista previa nuevos fletes:</b> Diurno ${cd_new:,} (con margen ${cd_m:,}) · Nocturno ${cn_new:,} (con margen ${cn_m:,})")
            ce1,ce2 = st.columns(2)
            with ce1:
                if st.button("💾 Guardar",use_container_width=True,key="red_save"):
                    try: supabase().table("rutas").update({"km":nkm,"tiempo_est":ntpo,"salida_max":nsal,"lat":nlat,"lon":nlon,"activa":nact}).eq("municipio",mun_ed).execute(); alerta("ok",f"<b>{mun_ed}</b> actualizada — fletes recalculados automáticamente."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
            with ce2:
                if st.button("🗑️ Eliminar",use_container_width=True,key="red_del"):
                    try: supabase().table("rutas").delete().eq("municipio",mun_ed).execute(); alerta("ok","Eliminada."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
        else: alerta("info","Sin rutas en BD. Usando datos por defecto.")
    with t2:
        st.markdown('<div class="dn-form"><div class="dn-form-title">NUEVA RUTA</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1: nmun=st.text_input("Municipio",key="nr_mun"); nkm2=st.number_input("KM desde Medellín",0.0,2000.0,100.0,step=0.1,key="nr_km"); ntpo2=st.text_input("Tiempo estimado",placeholder="2h 30m",key="nr_tpo")
        with c2: nsal2=st.text_input("Salida máx. (HH:MM)",placeholder="03:00",key="nr_sal"); nlat2=st.number_input("Latitud GPS",-90.0,90.0,7.0,step=0.0001,format="%.4f",key="nr_lat"); nlon2=st.number_input("Longitud GPS",-180.0,0.0,-75.5,step=0.0001,format="%.4f",key="nr_lon")
        if nkm2>0:
            cd=calcular_flete(nkm2,1,False,True); cn=calcular_flete(nkm2,1,True,True)
            _,cd_m=aplicar_margen(cd); _,cn_m=aplicar_margen(cn)
            alerta("info",f"Diurno <b>${cd:,}</b> (margen: ${cd_m:,}) · Nocturno <b>${cn:,}</b> (margen: ${cn_m:,})")
        if st.button("➕ Agregar",use_container_width=True,key="nr_add"):
            if not nmun or nkm2<=0: alerta("err","Ingresa nombre y km.")
            elif ":" not in nsal2: alerta("err","Formato hora: HH:MM")
            else:
                try: supabase().table("rutas").insert({"municipio":nmun.strip(),"km":nkm2,"tiempo_est":ntpo2,"salida_max":nsal2,"lat":nlat2,"lon":nlon2,"activa":True}).execute(); alerta("ok",f"<b>{nmun}</b> agregada."); st.rerun()
                except Exception as e: alerta("err",f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS Mapa ──────────────────────────────────────────────────
elif mod == "TMS" and subpag == "Mapa":
    banner("Mapa Operativo","CEDIs (🏠) · Rutas · Clientes · Puntos de reparto","tag-tms","GEO")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    rutas_df = get_rutas_db(); inv_df = get_inv(); cli_df = get_clientes()
    cedi_origen = st.selectbox("📍 Ver rutas desde CEDI:",CEDIS,key="mapa_cedi")
    sk_origen = stock_cedi(inv_df,cedi_origen)
    alerta("info",f"Stock disponible en <b>{cedi_origen}</b>: <b>{sk_origen:,} uds</b>")
    cm_,ci_ = st.columns([3,1])
    with cm_:
        if FOLIUM_OK and not rutas_df.empty:
            origen_coord = CEDI_COORDS.get(cedi_origen,[6.9,-75.5])
            m_ = folium.Map(location=[7.0,-75.5],zoom_start=7,tiles="CartoDB dark_matter")
            # ── CEDIs con icono de casa ──
            CEDI_DATA = {
                "Medellín": {"coord":[6.2442,-75.5812],"color":"blue","reparto":True},
                "Santa Rosa": {"coord":[6.6458,-75.4627],"color":"purple","reparto":True},
                "Taraza": {"coord":[7.5731,-75.4058],"color":"darkblue","reparto":True},
            }
            for cname,cinfo in CEDI_DATA.items():
                sk_c = stock_cedi(inv_df,cname)
                reparto_txt = " · Punto de reparto" if cinfo["reparto"] else ""
                folium.Marker(cinfo["coord"],
                    popup=folium.Popup(f"""<div style='font-family:sans-serif;min-width:160px'>
                        <b>🏠 CEDI {cname}</b><br>
                        Stock: {sk_c:,} uds<br>
                        Estado: Activo{reparto_txt}</div>""",max_width=200),
                    tooltip=f"🏠 CEDI {cname} — {sk_c:,} uds{reparto_txt}",
                    icon=folium.Icon(color=cinfo["color"],icon="home",prefix="fa")).add_to(m_)
            # Pereira marker
            folium.Marker([4.8087,-75.6906],
                popup="<b>📍 Pereira</b><br>Proveedores MP + Minoristas",
                tooltip="📍 Pereira — Proveedores y Minoristas",
                icon=folium.Icon(color="cadetblue",icon="map-marker",prefix="fa")).add_to(m_)
            # ── Clientes en el mapa ──
            if not cli_df.empty:
                for _,c in cli_df.iterrows():
                    c_lat = c.get("lat"); c_lon = c.get("lon")
                    if pd.notna(c_lat) and pd.notna(c_lon) and c_lat and c_lon:
                        tipo = str(c.get("tipo","mayorista"))
                        folium.Marker([float(c_lat),float(c_lon)],
                            popup=f"<b>{c.get('nombre','?')}</b><br>Tipo: {tipo}<br>CEDI: {c.get('cedi_asignado','—')}",
                            tooltip=f"{TIPO_ICON.get(tipo,'building')} {c.get('nombre','?')} ({tipo})",
                            icon=folium.Icon(color=TIPO_COLOR.get(tipo,"gray"),icon=TIPO_ICON.get(tipo,"building"),prefix="fa")).add_to(m_)
            # ── Rutas desde CEDI seleccionado ──
            pal = ["green","orange","red","darkgreen","lightred","pink"]
            act = rutas_df[rutas_df["activa"]==True] if "activa" in rutas_df.columns else rutas_df
            for i,(_,r) in enumerate(act.iterrows()):
                if pd.notna(r.get("lat")) and pd.notna(r.get("lon")):
                    fl_n = calcular_flete(r["km"],1,True,True)
                    _,fl_m = aplicar_margen(fl_n)
                    folium.Marker([r["lat"],r["lon"]],
                        popup=folium.Popup(f"""<div style='font-family:sans-serif'>
                            <b>🏘️ {r['municipio']}</b><br>
                            {r['km']} km desde Medellín<br>
                            Flete noc: ${fl_n:,}<br>
                            Con margen: ${fl_m:,}<br>
                            Salida máx: {r.get('salida_max','?')}</div>""",max_width=200),
                        tooltip=f"🏘️ {r['municipio']} ({r['km']}km)",
                        icon=folium.Icon(color=pal[i%len(pal)],icon="truck",prefix="fa")).add_to(m_)
                    folium.PolyLine([origen_coord,[r["lat"],r["lon"]]],color="#FF8C00",weight=2.5,opacity=0.75,dash_array="6 4").add_to(m_)
            # Resaltar origen
            folium.CircleMarker(origen_coord,radius=16,color="#00C97A",fill=True,fill_color="#00C97A",fill_opacity=0.2,
                tooltip=f"📍 Origen: {cedi_origen}").add_to(m_)
            st_folium(m_,width=None,height=540)
        else:
            if not FOLIUM_OK: alerta("warn","Instala: <code>pip install folium streamlit-folium</code>")
            else: alerta("info","Sin rutas registradas.")
    with ci_:
        st.markdown('<div class="dn-section"><div class="dn-section-header">CEDIs</div><div class="dn-section-body">', unsafe_allow_html=True)
        for nm in CEDIS:
            sk = stock_cedi(inv_df,nm)
            est = "🟢" if sk>cfg("stock_min")*2 else "🟡" if sk>cfg("stock_min") else "🔴"
            st.markdown(f'<div style="background:var(--bg4);border-radius:8px;padding:10px;margin-bottom:8px"><div style="font-size:10px;color:var(--txt3)">🏠 CEDI · Punto de reparto</div><div style="font-family:var(--cond);font-size:16px;font-weight:700;color:white">{est} {nm}</div><div style="font-family:var(--mono);font-size:20px;color:var(--accent)">{sk:,}</div><div style="font-size:10px;color:var(--txt3)">uds en stock</div></div>',unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="dn-section"><div class="dn-section-header">LEYENDA MAPA</div><div class="dn-section-body">', unsafe_allow_html=True)
        leyenda = [("🏠","CEDIs (Azul/Morado)","Casa — Almacén + Reparto"),("🏭","Proveedores (Rojo)","Suministros MP"),("⚙️","Fabricantes (Naranja)","Producción"),("🏢","Mayoristas (Azul)","Distribución"),("🛒","Minoristas (Verde)","Venta final"),("🚛","Destinos (Colores)","Rutas activas")]
        for ic,lab,desc in leyenda:
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border)"><div style="font-size:16px">{ic}</div><div><div style="font-size:11px;font-weight:600;color:var(--txt)">{lab}</div><div style="font-size:10px;color:var(--txt3)">{desc}</div></div></div>',unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS Órdenes de Servicio ────────────────────────────────────
elif mod == "TMS" and subpag == "Órdenes Servicio":
    banner("Órdenes de Servicio","Recolección · Transferencia · Entrega CEDI · Entrega Directa","tag-tms","ODS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    rutas_df = get_rutas_db(); veh_df = get_vehiculos(); inv_df = get_inv(); cli_df = get_clientes()
    ord_df = get_ordenes()
    veh_act = veh_df[veh_df["estado"]=="Activo"] if not veh_df.empty and "estado" in veh_df.columns else pd.DataFrame()
    cli_nombres = cli_df["nombre"].tolist() if not cli_df.empty and "nombre" in cli_df.columns else []
    TIPOS_ORDEN = {
        "recoleccion":           "🔴 Recolección MP — Proveedor → CEDI (recibir materia prima)",
        "recoleccion_fabricante":"🟣 Recolección PT — Fabricante → CEDI (recoger producto terminado/tortas)",
        "transferencia":         "🔵 Transferencia — CEDI → CEDI (mover stock entre bodegas)",
        "entrega_cedi":          "🟠 Entrega a CEDI — CEDI DistriNova → Bodega cliente",
        "entrega_directa":       "🟢 Entrega Directa — CEDI DistriNova → Cliente final (sin escala)",
    }
    t1,t2 = st.tabs(["📋  ÓRDENES REGISTRADAS","➕  NUEVA ORDEN"])
    with t1:
        if ord_df.empty:
            alerta("info","Sin órdenes de servicio. Crea la primera en ➕ Nueva Orden.")
        else:
            k1_,k2_,k3_,k4_ = st.columns(4)
            k1_.metric("Total Órdenes",len(ord_df))
            pend = len(ord_df[ord_df["estado"]=="pendiente"]) if "estado" in ord_df.columns else 0
            trans = len(ord_df[ord_df["estado"]=="en_transito"]) if "estado" in ord_df.columns else 0
            entg = len(ord_df[ord_df["estado"]=="entregado"]) if "estado" in ord_df.columns else 0
            k2_.metric("Pendientes",pend)
            k3_.metric("En Tránsito",trans)
            k4_.metric("Entregadas",entg)
            # Filter by type
            f_tipo = st.selectbox("Filtrar por tipo",["Todos"]+list(TIPOS_ORDEN.keys()),key="os_f_tipo")
            df_show = ord_df.copy()
            if f_tipo != "Todos" and "tipo_orden" in df_show.columns:
                df_show = df_show[df_show["tipo_orden"]==f_tipo]
            ok_c = [c for c in ["numero","tipo_orden","cliente_nombre","material","cantidad","unidad","origen","destino","destino_tipo","vehiculo","km","flete","estado","created_at"] if c in df_show.columns]
            st.dataframe(df_show[ok_c], use_container_width=True, hide_index=True)
            # Update estado
            st.markdown("---")
            st.markdown("**✏️ Actualizar estado de orden:**")
            if not ord_df.empty and "numero" in ord_df.columns:
                ord_sel = st.selectbox("Orden",ord_df["numero"].tolist(),key="os_upd_sel")
                new_est = st.selectbox("Nuevo estado",["pendiente","en_transito","entregado","cancelado"],key="os_upd_est")
                if st.button("Actualizar Estado",key="os_upd_btn"):
                    try:
                        supabase().table("ordenes_servicio").update({"estado":new_est}).eq("numero",ord_sel).execute()
                        # Registrar ingreso automáticamente al entregar
                        if new_est == "entregado":
                            row_os = ord_df[ord_df["numero"]==ord_sel]
                            if not row_os.empty:
                                flete_entregado = float(row_os["flete_con_margen"].values[0]) if "flete_con_margen" in row_os.columns else 0
                                cli_entregado = str(row_os["cliente_nombre"].values[0]) if "cliente_nombre" in row_os.columns else ""
                                try:
                                    cnt_f = supabase().table("facturas").select("id",count="exact").execute()
                                    nf_auto = f"FAC-{2001+(cnt_f.count or 0)}"
                                    supabase().table("facturas").insert({
                                        "numero":nf_auto,"cliente":cli_entregado,"nit":"",
                                        "cantidad":0,"precio_unit":flete_entregado,
                                        "costo_flete":flete_entregado,"subtotal":flete_entregado,
                                        "iva":0,"total":flete_entregado,
                                        "ruta":ord_sel,"usuario":usr_name
                                    }).execute()
                                    alerta("ok",f"Orden <b>{ord_sel}</b> → <b>Entregado</b> ✅ Ingreso <b>${int(flete_entregado):,}</b> registrado como {nf_auto}")
                                except:
                                    alerta("ok",f"Orden <b>{ord_sel}</b> → <b>{new_est}</b>")
                            else:
                                alerta("ok",f"Orden <b>{ord_sel}</b> → <b>{new_est}</b>")
                        else:
                            alerta("ok",f"Orden <b>{ord_sel}</b> → <b>{new_est}</b>")
                        st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
    with t2:
        st.markdown('<div class="dn-form"><div class="dn-form-title">NUEVA ORDEN DE SERVICIO</div>', unsafe_allow_html=True)
        tipo_sel = st.selectbox("Tipo de Orden",list(TIPOS_ORDEN.values()),key="os_tipo")
        tipo_key = [k for k,v in TIPOS_ORDEN.items() if v==tipo_sel][0]
        c1,c2 = st.columns(2)
        with c1:
            # Dynamic fields based on type
            if tipo_key == "recoleccion":
                alerta("info","<b>Recolección MP:</b> DistriNova va donde el proveedor (Pereira) y trae la materia prima al CEDI.")
                proveedores = cli_df[cli_df["tipo"]=="proveedor"]["nombre"].tolist() if not cli_df.empty and "tipo" in cli_df.columns else []
                os_cli = st.selectbox("Proveedor origen",proveedores if proveedores else ["Sin proveedores registrados"],key="os_cli")
                os_origen = st.selectbox("Ciudad proveedor",["Pereira","Medellín","Otra"],key="os_orig")
                os_destino = st.selectbox("CEDI destino",CEDIS,key="os_dest")
                os_destino_tipo = "cedi"
                os_material = st.text_input("Material a recoger",placeholder="Harina, Azúcar, Mantequilla...",key="os_mat")
                os_qty = st.number_input("Cantidad",1,value=500,key="os_qty")
                os_unidad = st.selectbox("Unidad",["kg","ton","sacos","L"],key="os_uni")
            elif tipo_key == "recoleccion_fabricante":
                alerta("info","<b>Recolección PT:</b> DistriNova va donde el fabricante (Medellín) y recoge el producto terminado (tortas) para almacenar en el CEDI.")
                fabricantes = cli_df[cli_df["tipo"]=="fabricante"]["nombre"].tolist() if not cli_df.empty and "tipo" in cli_df.columns else []
                os_cli = st.selectbox("Fabricante origen",fabricantes if fabricantes else ["Sin fabricantes registrados"],key="os_cli_f")
                os_origen = st.selectbox("Sede del fabricante",["Medellín","Otra"],key="os_orig_f")
                os_destino = st.selectbox("CEDI destino",CEDIS,key="os_dest_f")
                os_destino_tipo = "cedi"
                os_material = st.text_input("Producto a recoger",value="Tortas caseras",key="os_mat_f")
                os_qty = st.number_input("Cantidad (unidades)",1,value=168,key="os_qty_f")
                os_unidad = "unidades"
            elif tipo_key == "transferencia":
                alerta("info","<b>Transferencia:</b> Mover stock de un CEDI a otro.")
                os_cli = "DistriNova (interno)"
                os_origen = st.selectbox("CEDI origen",CEDIS,key="os_orig_t")
                os_destino = st.selectbox("CEDI destino",[c for c in CEDIS],key="os_dest_t")
                os_destino_tipo = "cedi"
                os_material = st.text_input("Material/Producto",placeholder="Tortas...",key="os_mat_t")
                os_qty = st.number_input("Cantidad (unidades)",1,99999999,168,key="os_qty_t")
                os_unidad = "unidades"
            elif tipo_key in ["entrega_cedi","entrega_directa"]:
                tipo_lbl = "a bodega del cliente" if tipo_key=="entrega_cedi" else "directa al cliente final"
                alerta("info",f"<b>Entrega {tipo_lbl}:</b> Sale del CEDI de DistriNova hacia el cliente.")
                os_cli = st.selectbox("Cliente destino",cli_nombres if cli_nombres else ["Sin clientes"],key="os_cli_e")
                os_origen = st.selectbox("CEDI origen (DistriNova)",CEDIS,key="os_orig_e")
                os_destino = st.text_input("Dirección de entrega",placeholder="Cra 10 #20-30, Pereira",key="os_dest_e")
                os_destino_tipo = "cedi" if tipo_key=="entrega_cedi" else "cliente_final"
                os_material = st.text_input("Material/Producto",placeholder="Tortas...",key="os_mat_e")
                os_qty = st.number_input("Cantidad (unidades)",1,value=168,key="os_qty_e")
                os_unidad = st.selectbox("Unidad",["unidades","kg","cajas"],key="os_uni_e")
            else:
                os_cli=""; os_origen="Medellín"; os_destino=""; os_destino_tipo="cedi"; os_material=""; os_qty=0; os_unidad="unidades"
        with c2:
            # Vehicle & route
            if not veh_act.empty:
                os_veh = st.selectbox("Vehículo",veh_act["codigo"].tolist(),key="os_veh")
                rv_os = veh_act[veh_act["codigo"]==os_veh].iloc[0]; cap_os = int(rv_os["capacidad"])
            else: os_veh="FRG-01"; cap_os=168
            # KM selection
            muns_disponibles = rutas_df["municipio"].tolist() if not rutas_df.empty else []
            os_ruta_mun = st.selectbox("Municipio/Ruta (para calcular flete)",["Medellín (interno)"]+muns_disponibles,key="os_ruta")
            if os_ruta_mun == "Medellín (interno)":
                os_km = st.number_input("KM (manual)",0.0,2000.0,0.0,step=0.1,key="os_km_m")
            else:
                ruta_row = rutas_df[rutas_df["municipio"]==os_ruta_mun].iloc[0]
                os_km = float(ruta_row["km"])
                st.metric("KM calculado",f"{os_km} km")
            os_noc = st.checkbox(f"Nocturno (+{cfg('recargo_nocturno_pct')}%)",value=True,key="os_noc")
            os_ida = st.checkbox("Incluir regreso vacío",value=True,key="os_ida")
            os_obs = st.text_area("Observaciones",height=68,key="os_obs")
        # Compute flete
        furgs_os = math.ceil(int(os_qty)/cap_os) if cap_os>0 and os_qty>0 else 1
        os_flete = calcular_flete(os_km,furgs_os,os_noc,os_ida) if os_km>0 else 0
        os_margen_val,os_total = aplicar_margen(os_flete)
        if os_flete>0:
            alerta("info",f"Flete base: <b>${os_flete:,}</b> · Margen {cfg('margen_pct')}%: <b>${os_margen_val:,}</b> · <b>Total a facturar: ${os_total:,}</b>")
        if tipo_key in ["recoleccion","recoleccion_fabricante"]:
            alerta("ok",f"✅ Esta orden AÑADIRÁ <b>{os_qty} {os_unidad}</b> al CEDI <b>{os_destino}</b> automáticamente al crear.")
        elif tipo_key == "transferencia":
            stk_orig = stock_cedi(inv_df,os_origen) if tipo_key=="transferencia" else 0
            if stk_orig < os_qty and tipo_key=="transferencia":
                alerta("warn",f"Stock CEDI {os_origen}: {stk_orig} uds. Orden podría superar disponible.")
            else:
                alerta("ok",f"✅ Esta orden moverá <b>{os_qty} uds</b> de {os_origen} → {os_destino}.")
        elif tipo_key in ["entrega_cedi","entrega_directa"]:
            stk_orig_e = stock_cedi(inv_df,os_origen) if tipo_key in ["entrega_cedi","entrega_directa"] else 0
            tipo_dst_lbl = "CEDI del cliente" if tipo_key=="entrega_cedi" else "cliente final (entrega directa)"
            if stk_orig_e < os_qty:
                alerta("warn",f"Stock CEDI {os_origen}: {stk_orig_e} uds — insuficiente para {os_qty}.")
            else:
                alerta("ok",f"✅ Esta orden DESCONTARÁ <b>{os_qty} uds</b> de {os_origen} → {tipo_dst_lbl}.")
        if st.button("🚀 Crear Orden de Servicio",use_container_width=True):
            # Validation
            ok_create = True
            if not os_material: alerta("err","Especifica el material."); ok_create=False
            if os_qty <= 0: alerta("err","Cantidad debe ser mayor a 0."); ok_create=False
            if tipo_key=="transferencia" and os_origen==os_destino: alerta("err","Origen y destino no pueden ser el mismo CEDI."); ok_create=False
            if ok_create:
                try:
                    db = supabase()
                    n_ord = len(get_ordenes())
                    num_os = f"OS-{datetime.now().year}-{n_ord+1:04d}"
                    cli_id = None
                    if cli_nombres and os_cli in cli_nombres:
                        cli_row2 = cli_df[cli_df["nombre"]==os_cli]
                        if not cli_row2.empty: cli_id = int(cli_row2["id"].values[0])
                    cli_tipo_act = ""
                    if not cli_df.empty and os_cli in cli_nombres:
                        r_cli = cli_df[cli_df["nombre"]==os_cli]
                        if not r_cli.empty: cli_tipo_act = str(r_cli["tipo"].values[0])
                    # Insert order
                    db.table("ordenes_servicio").insert({
                        "numero":num_os,"tipo_orden":tipo_key,"cliente_id":cli_id,
                        "cliente_nombre":os_cli,"tipo_actor":cli_tipo_act,
                        "material":os_material,"cantidad":int(os_qty),"unidad":os_unidad,
                        "origen":os_origen,"destino":os_destino,"destino_tipo":os_destino_tipo,
                        "vehiculo":os_veh,"km":float(os_km),"furgs":furgs_os,
                        "flete":float(os_flete),"flete_con_margen":float(os_total),
                        "estado":"pendiente","observaciones":os_obs,"usuario":usr_name
                    }).execute()
                    # Auto inventory update
                    if tipo_key in ["recoleccion","recoleccion_fabricante"]:
                        sk_dest = stock_cedi(get_inv(),os_destino)
                        db.table("inventario").update({"stock":sk_dest+int(os_qty),"updated_at":datetime.now().isoformat()}).eq("cedi",os_destino).execute()
                        db.table("movimientos").insert({"cedi":os_destino,"tipo":"entrada","cantidad":int(os_qty),"documento":num_os,"stock_result":sk_dest+int(os_qty),"usuario":usr_name}).execute()
                    elif tipo_key == "transferencia":
                        sk_orig2 = stock_cedi(get_inv(),os_origen)
                        sk_dest2 = stock_cedi(get_inv(),os_destino)
                        if sk_orig2 >= int(os_qty):
                            db.table("inventario").update({"stock":sk_orig2-int(os_qty),"updated_at":datetime.now().isoformat()}).eq("cedi",os_origen).execute()
                            db.table("inventario").update({"stock":sk_dest2+int(os_qty),"updated_at":datetime.now().isoformat()}).eq("cedi",os_destino).execute()
                            db.table("movimientos").insert({"cedi":os_origen,"tipo":"salida","cantidad":int(os_qty),"documento":num_os,"stock_result":sk_orig2-int(os_qty),"usuario":usr_name}).execute()
                            db.table("movimientos").insert({"cedi":os_destino,"tipo":"entrada","cantidad":int(os_qty),"documento":num_os,"stock_result":sk_dest2+int(os_qty),"usuario":usr_name}).execute()
                    elif tipo_key in ["entrega_cedi","entrega_directa"]:
                        sk_orig3 = stock_cedi(get_inv(),os_origen)
                        if sk_orig3 >= int(os_qty):
                            db.table("inventario").update({"stock":sk_orig3-int(os_qty),"updated_at":datetime.now().isoformat()}).eq("cedi",os_origen).execute()
                            db.table("movimientos").insert({"cedi":os_origen,"tipo":"salida","cantidad":int(os_qty),"documento":num_os,"stock_result":sk_orig3-int(os_qty),"usuario":usr_name}).execute()
                    alerta("ok",f"✅ Orden <b>{num_os}</b> creada — Inventario actualizado automáticamente."); st.balloons(); st.rerun()
                except Exception as e: alerta("err",f"Error al crear orden: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS Pedidos Comerciales ────────────────────────────────────
elif mod == "TMS" and subpag == "Solicitudes Servicio":
    banner("Solicitudes de Servicio","El cliente solicita un servicio → se cotiza → se aprueba → genera Orden de Servicio","tag-tms","SS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alerta("info","💡 <b>¿Qué es una Solicitud de Servicio?</b> Es la petición formal de un cliente para que DistriNova le preste un servicio logístico: transporte por flete, almacenamiento por días, o ambos. Al aprobarla, el sistema genera la Orden de Servicio automáticamente.")
    pc_df = get_pedidos_comerciales(); cli_df = get_clientes()
    rutas_df = get_rutas_db(); veh_df = get_vehiculos()
    cli_nombres = cli_df["nombre"].tolist() if not cli_df.empty and "nombre" in cli_df.columns else []
    veh_act = veh_df[veh_df["estado"]=="Activo"] if not veh_df.empty and "estado" in veh_df.columns else pd.DataFrame()
    t1,t2 = st.tabs(["📋  SOLICITUDES REGISTRADAS","➕  NUEVA SOLICITUD"])
    with t1:
        if pc_df.empty:
            alerta("info","Sin solicitudes. Crea la primera en ➕ Nueva Solicitud.")
        else:
            k1_,k2_,k3_,k4_ = st.columns(4)
            k1_.metric("Total",len(pc_df))
            pend_pc = len(pc_df[pc_df["estado"]=="pendiente"]) if "estado" in pc_df.columns else 0
            apro_pc = len(pc_df[pc_df["estado"]=="aprobado"]) if "estado" in pc_df.columns else 0
            comp_pc = len(pc_df[pc_df["estado"]=="completado"]) if "estado" in pc_df.columns else 0
            k2_.metric("Pendientes",pend_pc); k3_.metric("Aprobados",apro_pc); k4_.metric("Completados",comp_pc)
            total_facturar = pc_df["total"].sum() if "total" in pc_df.columns else 0
            k4_.metric("Total a facturar",f"${total_facturar:,.0f}")
            ok_c = [c for c in ["numero","cliente_nombre","tipo_actor","material","cantidad","unidad","total","estado","orden_numero","observaciones","created_at"] if c in pc_df.columns]
            st.dataframe(pc_df[ok_c], use_container_width=True, hide_index=True)
            st.markdown("---")
            st.markdown("**⚡ Aprobar solicitud y generar Orden de Servicio:**")
            pendientes = pc_df[pc_df["estado"]=="pendiente"] if "estado" in pc_df.columns else pd.DataFrame()
            if not pendientes.empty and "numero" in pendientes.columns:
                pc_sel = st.selectbox("Solicitud a aprobar",pendientes["numero"].tolist(),key="pc_apro_sel")
                pc_row = pendientes[pendientes["numero"]==pc_sel].iloc[0]
                st.caption(f"Cliente: **{pc_row.get('cliente_nombre','—')}** | Servicio: {pc_row.get('material','—')} | Total acordado: **${float(pc_row.get('total',0)):,.0f}**")
                if st.button(f"✅ Aprobar y Generar OS",key="pc_apro_btn",use_container_width=True):
                    try:
                        db = supabase()
                        n_ord = len(get_ordenes())
                        num_os_pc = f"OS-{datetime.now().year}-{n_ord+1:04d}"
                        db.table("ordenes_servicio").insert({
                            "numero":num_os_pc,"tipo_orden":"entrega_directa",
                            "cliente_nombre":pc_row.get("cliente_nombre",""),
                            "tipo_actor":pc_row.get("tipo_actor",""),
                            "material":pc_row.get("material",""),"cantidad":int(pc_row.get("cantidad",0)),
                            "unidad":pc_row.get("unidad","unidades"),
                            "origen":"Medellín","destino":pc_row.get("cliente_nombre",""),"destino_tipo":"cliente_final",
                            "km":0.0,"furgs":1,"flete":float(pc_row.get("total",0)),"flete_con_margen":float(pc_row.get("total",0)),
                            "estado":"pendiente","observaciones":f"SS {pc_sel}: {pc_row.get('observaciones','')}","usuario":usr_name,
                            "pedido_origen":pc_sel
                        }).execute()
                        db.table("pedidos_comerciales").update({"estado":"aprobado","orden_numero":num_os_pc}).eq("numero",pc_sel).execute()
                        alerta("ok",f"✅ Solicitud aprobada. Orden <b>{num_os_pc}</b> generada. Ve a Órdenes de Servicio para asignar vehículo y ruta."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
            else:
                alerta("info","No hay solicitudes pendientes de aprobación.")
    with t2:
        st.markdown('<div class="dn-form"><div class="dn-form-title">NUEVA SOLICITUD DE SERVICIO</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            pc_cli = st.selectbox("Cliente que solicita",cli_nombres if cli_nombres else ["Sin clientes"],key="pc_cli")
            cli_tipo_pc = ""
            if cli_nombres and not cli_df.empty:
                r_pc = cli_df[cli_df["nombre"]==pc_cli]
                if not r_pc.empty: cli_tipo_pc = str(r_pc["tipo"].values[0])
            st.caption(f"Tipo de actor: **{cli_tipo_pc}**")
            pc_tipo_servicio = st.selectbox("¿Qué servicio necesita?",
                ["Transporte (flete)","Almacenamiento","Transporte + Almacenamiento","Recolección en origen"],key="pc_tipo_svc")
            pc_mat = st.text_input("Descripción del servicio / Producto",
                placeholder="Ej: Transporte 168 tortas a Caucasia, Almacenamiento 2 ton harina...",key="pc_mat")
            pc_obs = st.text_area("Detalles adicionales (ruta, fecha, condiciones)",height=80,key="pc_obs")
        with c2:
            # Cotización automática según tipo servicio
            if pc_tipo_servicio in ["Transporte (flete)","Transporte + Almacenamiento","Recolección en origen"]:
                pc_ruta = st.selectbox("Ruta / Municipio",rutas_df["municipio"].tolist() if not rutas_df.empty else [],key="pc_ruta")
                pc_qty  = st.number_input("Cantidad a transportar",1,value=168,key="pc_qty")
                pc_unidad = st.selectbox("Unidad",["unidades","kg","ton","cajas","sacos","L"],key="pc_unidad")
                pc_veh  = st.selectbox("Vehículo",veh_act["codigo"].tolist() if not veh_act.empty else ["FRG-01"],key="pc_veh")
                pc_noc  = st.checkbox("Nocturno",value=True,key="pc_noc")
                ruta_row_pc = rutas_df[rutas_df["municipio"]==pc_ruta].iloc[0] if not rutas_df.empty and pc_ruta else None
                pc_km = float(ruta_row_pc["km"]) if ruta_row_pc is not None else 0
                rv_pc = veh_act[veh_act["codigo"]==pc_veh].iloc[0] if not veh_act.empty and pc_veh in veh_act["codigo"].values else None
                cap_pc = int(rv_pc["capacidad"]) if rv_pc is not None else 168
                furgs_pc = math.ceil(pc_qty/cap_pc) if cap_pc>0 else 1
                flete_pc = calcular_flete(pc_km,furgs_pc,pc_noc,True)
                _,total_transp = aplicar_margen(flete_pc)
                st.metric(f"Flete estimado ({furgs_pc} veh.)",f"${total_transp:,}")
            else:
                pc_qty=0; total_transp=0; pc_km=0; furgs_pc=1
            if pc_tipo_servicio in ["Almacenamiento","Transporte + Almacenamiento"]:
                pc_ton = st.number_input("Peso (toneladas)",0.01,1000.0,0.5,step=0.01,key="pc_ton")
                pc_dias_alm = st.number_input("Días estimados de almacenamiento",1,365,30,key="pc_dias_alm")
                total_alm,_ = aplicar_margen(costo_almacenamiento(pc_ton,pc_dias_alm))
                st.metric(f"Almacenamiento estimado ({pc_dias_alm}d)",f"${total_alm:,}")
            else:
                total_alm=0
            pc_tot = total_transp + total_alm
            st.metric("💰 TOTAL A FACTURAR",f"${pc_tot:,}")
        if st.button("📝 Registrar Solicitud",use_container_width=True):
            if not pc_mat: alerta("err","Describe el servicio solicitado.")
            else:
                try:
                    n_pc = len(get_pedidos_comerciales())
                    num_pc = f"SS-{datetime.now().year}-{n_pc+1:04d}"
                    cli_id_pc = None
                    if cli_nombres and not cli_df.empty:
                        r_pc2 = cli_df[cli_df["nombre"]==pc_cli]
                        if not r_pc2.empty: cli_id_pc = int(r_pc2["id"].values[0])
                    supabase().table("pedidos_comerciales").insert({
                        "numero":num_pc,"cliente_id":cli_id_pc,"cliente_nombre":pc_cli,"tipo_actor":cli_tipo_pc,
                        "material":pc_mat,"cantidad":pc_qty,"unidad":"servicios",
                        "precio_unit":float(pc_tot),"total":float(pc_tot),
                        "estado":"pendiente","observaciones":f"{pc_tipo_servicio} | {pc_obs}","usuario":usr_name
                    }).execute()
                    alerta("ok",f"✅ Solicitud <b>{num_pc}</b> registrada por <b>${pc_tot:,}</b>. Apruébala para generar la Orden de Servicio."); st.rerun()
                except Exception as e: alerta("err",f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── FIN Dashboard Financiero ───────────────────────────────────
elif mod == "FIN" and subpag == "Dashboard Financiero":
    banner("Dashboard Financiero","Ingresos · Egresos · Utilidad · Resumen por período","tag-fin","FIN")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    ord_df2 = get_ordenes()
    fac_df = db_get("facturas", order="created_at", desc=True)
    # ── Ingresos desde facturas
    total_ing = int(fac_df["total"].sum()) if not fac_df.empty and "total" in fac_df.columns else 0
    num_facturas = len(fac_df) if not fac_df.empty else 0
    # ── Ingresos potenciales (OS pendientes o en tránsito)
    if not ord_df2.empty and "flete_con_margen" in ord_df2.columns:
        ing_pendiente = int(ord_df2[ord_df2["estado"].isin(["pendiente","en_transito"])]["flete_con_margen"].sum())
        ing_entregado = int(ord_df2[ord_df2["estado"]=="entregado"]["flete_con_margen"].sum())
        num_os_entregadas = len(ord_df2[ord_df2["estado"]=="entregado"])
    else:
        ing_pendiente = 0; ing_entregado = 0; num_os_entregadas = 0
    # ── Egresos (costos estimados de OS entregadas)
    egresos = 0
    if not ord_df2.empty and "km" in ord_df2.columns:
        for _,ro in ord_df2[ord_df2["estado"]=="entregado"].iterrows():
            km_r = float(ro.get("km",0)); f_r = int(ro.get("furgs",1) or 1)
            c_dir = int(km_r*f_r*(cfg("costo_combustible_km")+cfg("costo_mantenimiento_km"))+f_r*(cfg("costo_conductor_dia")+cfg("costo_peaje_promedio")))
            egresos += int(c_dir*(1+cfg("costos_indirectos_pct")/100))
    utilidad = ing_entregado - egresos
    margen_u = round(utilidad/ing_entregado*100,1) if ing_entregado>0 else 0
    # ── Métricas top
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("💰 Ingresos cobrados",f"${total_ing:,}",f"{num_facturas} facturas")
    k2.metric("✅ Facturado (OS entregadas)",f"${ing_entregado:,}",f"{num_os_entregadas} órdenes")
    k3.metric("⏳ Por cobrar (pendientes)",f"${ing_pendiente:,}")
    k4.metric("📉 Egresos estimados",f"${egresos:,}")
    k5.metric("📈 Utilidad neta",f"${utilidad:,}",f"{margen_u}% margen")
    st.divider()
    # ── Tabla de facturas
    col_left, col_right = st.columns([3,2])
    with col_left:
        st.markdown('<div class="dn-section"><div class="dn-section-header">FACTURAS EMITIDAS</div><div class="dn-section-body">', unsafe_allow_html=True)
        if not fac_df.empty:
            cols_fac = [c for c in ["numero","cliente","ruta","subtotal","total","usuario","created_at"] if c in fac_df.columns]
            st.dataframe(fac_df[cols_fac], use_container_width=True, hide_index=True)
        else:
            alerta("info","Sin facturas. Al marcar una OS como Entregado se genera automáticamente.")
        st.markdown('</div></div>', unsafe_allow_html=True)
    with col_right:
        st.markdown('<div class="dn-section"><div class="dn-section-header">ÓRDENES ENTREGADAS</div><div class="dn-section-body">', unsafe_allow_html=True)
        if not ord_df2.empty:
            entregadas = ord_df2[ord_df2["estado"]=="entregado"]
            if not entregadas.empty:
                cols_e = [c for c in ["numero","cliente_nombre","material","flete_con_margen","created_at"] if c in entregadas.columns]
                st.dataframe(entregadas[cols_e], use_container_width=True, hide_index=True)
            else:
                alerta("info","Aún no hay órdenes entregadas.")
        st.markdown('</div></div>', unsafe_allow_html=True)
    # ── Registro manual de egreso
    st.divider()
    st.markdown('<div class="dn-section"><div class="dn-section-header">REGISTRAR EGRESO MANUAL</div><div class="dn-section-body">', unsafe_allow_html=True)
    c1e,c2e = st.columns(2)
    with c1e:
        eg_desc = st.text_input("Descripción del egreso",placeholder="Mantenimiento FRG-01, Combustible semana...",key="eg_desc")
        eg_monto = st.number_input("Monto ($)",0,50000000,0,step=10000,key="eg_monto")
    with c2e:
        eg_cat = st.selectbox("Categoría",["Combustible","Mantenimiento","Conductor","Peajes","Arriendo CEDI","Admin","Otro"],key="eg_cat")
        eg_fecha = st.date_input("Fecha",value=date.today(),key="eg_fecha")
    if st.button("💾 Registrar Egreso",use_container_width=True,key="eg_save"):
        if not eg_desc or eg_monto==0: alerta("err","Completa descripción y monto.")
        else:
            try:
                supabase().table("facturas").insert({
                    "numero":f"EGR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "cliente":f"EGRESO: {eg_cat}","nit":"",
                    "cantidad":0,"precio_unit":-eg_monto,
                    "costo_flete":0,"subtotal":-eg_monto,
                    "iva":0,"total":-eg_monto,
                    "ruta":eg_desc,"usuario":usr_name
                }).execute()
                alerta("ok",f"Egreso <b>{eg_cat}: {eg_desc}</b> — <b>-${eg_monto:,}</b> registrado.")
                st.rerun()
            except Exception as e: alerta("err",f"Error: {e}")
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── FIN Cotizador ──────────────────────────────────────────────
elif mod == "FIN" and subpag == "Cotizador":
    banner("Cotizador Logístico","Transporte + Almacenamiento + Margen% · DistriNova factura servicios","tag-fin","FIN")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alerta("info",f"DistriNova es <b>operador logístico</b>. Factura al cliente por servicios. Margen actual: <b>{cfg('margen_pct')}%</b>")
    rutas_df = get_rutas_db(); veh_df = get_vehiculos(); cli_df = get_clientes()
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div class="dn-form"><div class="dn-form-title">PARÁMETROS</div>', unsafe_allow_html=True)
        rc_ = st.selectbox("Ruta",rutas_df["municipio"].tolist() if not rutas_df.empty else [],key="cot_ruta")
        cli_nombres_cot = cli_df["nombre"].tolist() if not cli_df.empty and "nombre" in cli_df.columns else []
        cli_cot = st.selectbox("Cliente",["— Sin cliente —"]+cli_nombres_cot,key="cot_cli")
        qty_c = st.number_input("Unidades",1,value=168,key="cot_qty")
        dalm = st.number_input("Días almacenamiento",0,365,1,key="cot_dalm")
        peso_ton_cot = st.number_input("Peso total (toneladas)",0.0,1000.0,0.1,step=0.01,format="%.2f",key="cot_ton")
        noc_c = st.checkbox(f"Nocturna (+{cfg('recargo_nocturno_pct')}%)",value=True,key="cot_noc")
        ida_c = st.checkbox("Regreso vacío",value=True,key="cot_ida")
        veh_act_ = veh_df[veh_df["estado"]=="Activo"] if not veh_df.empty and "estado" in veh_df.columns else pd.DataFrame()
        if not veh_act_.empty:
            vs_ = st.selectbox("Vehículo",veh_act_["codigo"].tolist(),key="cot_veh")
            cap_v2 = int(veh_act_[veh_act_["codigo"]==vs_].iloc[0]["capacidad"])
        else: cap_v2 = 168
        st.markdown('</div>', unsafe_allow_html=True)
    if rc_ and not rutas_df.empty:
        rd_ = rutas_df[rutas_df["municipio"]==rc_].iloc[0]
        furgs2 = math.ceil(qty_c/cap_v2)
        c_fl2 = calcular_flete(rd_["km"],furgs2,noc_c,ida_c)
        c_alm2 = costo_almacenamiento(peso_ton_cot, dalm) if dalm>0 else 0
        c_ali2 = qty_c * cfg("tarifa_alistamiento")
        c_man2 = qty_c * cfg("tarifa_manipulacion")
        c_adm2 = int(c_fl2 * cfg("tarifa_admin_pct") / 100)
        subtotal2 = c_fl2 + c_alm2 + c_ali2 + c_man2 + c_adm2
        margen2,total_con_margen2 = aplicar_margen(subtotal2)
        ppu2 = total_con_margen2 // qty_c if qty_c else 0
        with c2:
            st.markdown('<div class="dn-section"><div class="dn-section-header">DESGLOSE DE COBRO</div><div class="dn-section-body">', unsafe_allow_html=True)
            km_total = float(rd_["km"]) * 2 if ida_c else float(rd_["km"])
            alerta("info",f"Transporte: {km_total:.0f}km × ${cfg('tarifa_km'):,}/km × {furgs2} veh × {'1.30 noc' if noc_c else '1.00'} = <b>${c_fl2:,}</b>")
            if dalm > 0:
                alerta("info",f"Almacenamiento: {peso_ton_cot:.2f} ton × ${cfg('tarifa_alm_ton_dia'):,}/ton/día × {dalm}d = <b>${c_alm2:,}</b>")
            st.dataframe(pd.DataFrame({
                "Servicio":["🚐 Transporte",f"🏭 Almacenamiento ({dalm}d)","📦 Alistamiento","🔄 Manipulación",f"📋 Admin {cfg('tarifa_admin_pct')}%","— Subtotal —",f"📈 Margen {cfg('margen_pct')}%"],
                "Cobro":[f"${c_fl2:,}",f"${c_alm2:,}",f"${c_ali2:,}",f"${c_man2:,}",f"${c_adm2:,}",f"${subtotal2:,}",f"${margen2:,}"]
            }), use_container_width=True, hide_index=True)
            k1_,k2_,k3_ = st.columns(3)
            k1_.metric("Subtotal",f"${subtotal2:,}")
            k2_.metric(f"Margen {cfg('margen_pct')}%",f"${margen2:,}")
            k3_.metric("TOTAL A FACTURAR",f"${total_con_margen2:,}")
            alerta("ok",f"Facturar <b>${total_con_margen2:,}</b> a {cli_cot} · Ingreso/ud: ${ppu2:,}")
            st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── FIN P&G por Ruta ──────────────────────────────────────────
elif mod == "FIN" and subpag == "P&G por Ruta":
    banner("Rentabilidad por Ruta","P&G · Márgenes · Costos vs Ingresos","tag-fin","P&G")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    rutas_df = get_rutas_db(); desp_df = get_desp(); veh_df = get_vehiculos()
    veh_act = veh_df[veh_df["estado"]=="Activo"] if not veh_df.empty and "estado" in veh_df.columns else pd.DataFrame()
    cap_v_avg = int(veh_act["capacidad"].mean()) if not veh_act.empty and "capacidad" in veh_act.columns else 168
    total_ing = int(desp_df["costo_flete"].sum()) if not desp_df.empty and "costo_flete" in desp_df.columns else 0
    total_uds = int(desp_df["tortas"].sum()) if not desp_df.empty and "tortas" in desp_df.columns else 0
    total_costos = 0
    if not desp_df.empty and "km" in desp_df.columns and "furgonetas" in desp_df.columns:
        for _,d in desp_df.iterrows():
            km_d = float(d.get("km",0)); furgs_d = int(d.get("furgonetas",1))
            total_costos += int(km_d*furgs_d*(cfg("costo_combustible_km")+cfg("costo_mantenimiento_km"))+furgs_d*(cfg("costo_conductor_dia")+cfg("costo_peaje_promedio")))
    utilidad = total_ing - total_costos
    margen_real = round(utilidad/total_ing*100,1) if total_ing>0 else 0
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("💰 Ingresos Totales",f"${total_ing:,}")
    k2.metric("📉 Costos Operativos",f"${total_costos:,}")
    k3.metric("✅ Utilidad Bruta",f"${utilidad:,}",f"{margen_real}% margen")
    k4.metric("📦 Ingreso/Torta",f"${total_ing//total_uds:,}" if total_uds>0 else "—")
    st.divider()
    st.markdown('<div class="dn-section"><div class="dn-section-header">P&G SIMULADO — 1 furgoneta nocturna, ida/vuelta</div><div class="dn-section-body">', unsafe_allow_html=True)
    act = rutas_df[rutas_df["activa"]==True] if "activa" in rutas_df.columns else rutas_df
    pnl = []
    for _,r in act.iterrows():
        km = float(r["km"]); km2 = km*2
        ing = calcular_flete(km,1,True,True)
        mg_val,ing_con_mg = aplicar_margen(ing)
        costo = calcular_costos_operativos(km,1,True)
        util_r = ing_con_mg - costo
        margen_r = round(util_r/ing_con_mg*100,1) if ing_con_mg>0 else 0
        pnl.append({"Municipio":r["municipio"],"KM i/v":km2,
                    "Flete base":f"${ing:,}",f"Margen {cfg('margen_pct')}%":f"${mg_val:,}","Total facturado":f"${ing_con_mg:,}",
                    "Costo operativo":f"${costo:,}","Utilidad neta":f"${util_r:,}","Margen neto %":f"{margen_r}%",
                    "Salida máx.":r.get("salida_max","—")})
    st.dataframe(pd.DataFrame(pnl), use_container_width=True, hide_index=True)
    st.markdown('</div></div>', unsafe_allow_html=True)
    gc1,gc2 = st.columns(2)
    with gc1:
        rutas_n = [r["municipio"] for _,r in act.iterrows()]
        ingresos_ = [calcular_flete(float(r["km"]),1,True,True) for _,r in act.iterrows()]
        ingresos_mg = [aplicar_margen(i)[1] for i in ingresos_]
        costos_ = [calcular_costos_operativos(float(r["km"]),1,True) for _,r in act.iterrows()]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Ingreso c/margen",x=rutas_n,y=ingresos_mg,marker_color="#00C97A",opacity=0.85))
        fig.add_trace(go.Bar(name="Costo op.",x=rutas_n,y=costos_,marker_color="#FF4444",opacity=0.75))
        fig.update_layout(barmode="group",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(font=dict(color="#5A7A99",size=11)),height=280,margin=dict(t=16,b=4,l=4,r=4),
            xaxis=dict(tickfont=dict(size=10,color="#5A7A99")),yaxis=dict(gridcolor="rgba(255,255,255,.04)",tickfont=dict(size=10,color="#5A7A99")))
        st.plotly_chart(fig,use_container_width=True)
    with gc2:
        utils_ = [aplicar_margen(calcular_flete(float(r["km"]),1,True,True))[1]-calcular_costos_operativos(float(r["km"]),1,True) for _,r in act.iterrows()]
        tot_mg = [aplicar_margen(calcular_flete(float(r["km"]),1,True,True))[1] for _,r in act.iterrows()]
        margenes_ = [round(u/t*100,1) if t>0 else 0 for u,t in zip(utils_,tot_mg)]
        colors_ = ["#00C97A" if m>30 else "#FFB800" if m>15 else "#FF4444" for m in margenes_]
        fig2 = go.Figure(go.Bar(x=rutas_n,y=margenes_,marker_color=colors_,opacity=0.9,
            text=[f"{m}%" for m in margenes_],textposition="outside",textfont=dict(color="rgba(200,216,234,.8)",size=11)))
        fig2.update_layout(title="Margen neto % por ruta",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
            height=280,margin=dict(t=36,b=4,l=4,r=4),title_font=dict(color="#C8D8EA",size=12),
            xaxis=dict(tickfont=dict(size=10,color="#5A7A99")),yaxis=dict(gridcolor="rgba(255,255,255,.04)",tickfont=dict(size=10,color="#5A7A99")))
        st.plotly_chart(fig2,use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── FIN Documentos (+ Historial integrado) ─────────────────────
elif mod == "FIN" and subpag == "Documentos":
    banner("Documentos y Registros","Remisiones · Facturas · Historial de operaciones","tag-fin","DOCS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    t1,t2,t3 = st.tabs(["📄  REMISIONES","🧾  FACTURAS","📊  HISTORIAL OPERACIONES"])
    with t1:
        df_ = get_desp()
        if not df_.empty and "remision" in df_.columns:
            sel_ = st.selectbox("Despacho",df_["remision"].tolist(),key="rem_sel")
            row_ = df_[df_["remision"]==sel_].iloc[0]
            st.markdown(f"### 📄 {sel_}\n| Campo | Valor |\n|---|---|\n| Empresa | DistriNova |\n| Número | {sel_} |\n| Fecha | {str(row_.get('created_at',''))[:10]} |\n| Origen | {row_['cedi_origen']} |\n| Destino | {row_['destino']} |\n| KM | {row_['km']} |\n| Unidades | **{row_['tortas']}** |\n| Furgonetas | {row_['furgonetas']} |\n| Jornada | {'Nocturna' if row_['nocturno'] else 'Diurna'} |\n| **Flete base** | **${int(row_['costo_flete']):,}** |\n| Responsable | {row_.get('usuario','—')} |")
        else: alerta("info","Sin despachos registrados.")
    with t2:
        c1_,c2_ = st.columns(2)
        with c1_:
            clf_ = st.text_input("Cliente",key="fac_cli"); nit_ = st.text_input("NIT",key="fac_nit")
            ffl_ = st.number_input("Cobro transporte ($)",0,key="fac_fl")
            fal_ = st.number_input("Almacenamiento ($)",0,key="fac_alm")
            fas_ = st.number_input("Alistamiento ($)",0,key="fac_ali")
            fma_ = st.number_input("Manipulación ($)",0,key="fac_man")
        with c2_:
            sub_ = ffl_+fal_+fas_+fma_
            mg_fac,tot_mg_fac = aplicar_margen(sub_)
            tot_ = tot_mg_fac  # Sin IVA
            k1_,k2_,k3_ = st.columns(3)
            k1_.metric("Subtotal servicios",f"${sub_:,}")
            k2_.metric(f"Margen {cfg('margen_pct')}%",f"+${mg_fac:,}")
            k3_.metric("TOTAL A FACTURAR",f"${tot_:,}")
            if st.button("Guardar Factura",use_container_width=True):
                if not clf_: alerta("err","Ingresa cliente.")
                else:
                    try:
                        cnt_ = supabase().table("facturas").select("id",count="exact").execute()
                        nf_ = f"FAC-{2001+(cnt_.count or 0)}"
                        supabase().table("facturas").insert({"numero":nf_,"cliente":clf_,"nit":nit_,"cantidad":0,"precio_unit":sub_,"costo_flete":ffl_,"subtotal":sub_,"iva":iva_,"total":tot_,"ruta":"Servicios logísticos","usuario":usr_name}).execute()
                        alerta("ok",f"Factura <b>{nf_}</b> — Total:<b>${tot_:,}</b>")
                    except Exception as e: alerta("err",f"Error: {e}")
    with t3:
        alerta("info","Vista consolidada de todas las operaciones. <b>Órdenes de Servicio</b> = la operación física. <b>Solicitudes de Servicio</b> = el acuerdo comercial previo. <b>Movimientos</b> = cambios automáticos de inventario.")
        ord_df = get_ordenes(); pc_df = get_pedidos_comerciales(); mf_ = get_mov(); alm_h = get_alm_clientes()
        k1_,k2_,k3_,k4_ = st.columns(4)
        k1_.metric("Órdenes Servicio",len(ord_df))
        k2_.metric("Solicitudes",len(pc_df))
        k3_.metric("Movimientos inv.",len(mf_))
        k4_.metric("Almacenamientos",len(alm_h))
        ta,tb,tc,td = st.tabs(["📋 Órdenes Servicio","📝 Solicitudes","📦 Movimientos inventario","🏭 Almacenamientos"])
        with ta: st.dataframe(ord_df[[c for c in ["numero","tipo_orden","cliente_nombre","material","cantidad","origen","destino","vehiculo","flete_con_margen","estado","created_at"] if c in ord_df.columns]] if not ord_df.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
        with tb: st.dataframe(pc_df[[c for c in ["numero","cliente_nombre","tipo_actor","material","total","estado","orden_numero","created_at"] if c in pc_df.columns]] if not pc_df.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
        with tc: st.dataframe(mf_ if not mf_.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
        with td: st.dataframe(alm_h[[c for c in ["cliente_nombre","tipo_actor","material","cantidad","unidad","peso_ton","fecha_ingreso","dias_calculados" if "dias_calculados" in alm_h.columns else "fecha_ingreso","cedi","estado"] if c in alm_h.columns]] if not alm_h.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── FIN Historial (redirect to Documentos) ─────────────────────
elif mod == "FIN" and subpag == "Historial":
    st.session_state.subpag = "Documentos"; st.rerun()
# ── SYS Flota ──────────────────────────────────────────────────
elif mod == "SYS" and subpag == "Flota":
    banner("Gestión de Flota","4 Furgonetas (168 uds) · 5 Turbos Plataforma Doble (1,000 uds)","tag-sys","FLOTA")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    veh_df = get_vehiculos()
    # Summary stats
    if not veh_df.empty:
        act_v = veh_df[veh_df["estado"]=="Activo"] if "estado" in veh_df.columns else veh_df
        k1_,k2_,k3_,k4_ = st.columns(4)
        k1_.metric("Vehículos activos",len(act_v))
        k2_.metric("Cap. flota activa",f"{int(act_v['capacidad'].sum()) if 'capacidad' in act_v.columns else 0:,} tortas")
        furg_act = act_v[act_v["tipo"]=="Furgoneta"] if "tipo" in act_v.columns else pd.DataFrame()
        turbo_act = act_v[act_v["tipo"].str.contains("Turbo",na=False)] if "tipo" in act_v.columns else pd.DataFrame()
        k3_.metric("Furgonetas activas",len(furg_act))
        k4_.metric("Turbos activos",len(turbo_act))
    alerta("info","<b>Turbos con Plataforma Doble:</b> 6 arrumes máx (vs 3 estándar). La plataforma adicional duplica la capacidad de apilamiento, permitiendo 1,000 tortas/viaje vs 168 de furgoneta.")
    if not veh_df.empty:
        nc = min(5,len(veh_df)); cols_ = st.columns(nc)
        for i,(_,v) in enumerate(veh_df.iterrows()):
            with cols_[i%nc]:
                ec_ = "status-ok" if v.get("estado")=="Activo" else "status-warn" if v.get("estado")=="Reserva" else "status-err"
                color_veh = "#FF8C00" if "Turbo" in str(v.get("tipo","")) else "#1E88E5"
                st.markdown(f'<div class="veh-card"><div class="veh-status"><span class="dn-status {ec_}">{v.get("estado","—")}</span></div><div class="veh-codigo">{v.get("codigo","")}</div><div class="veh-tipo" style="color:{color_veh}">{v.get("tipo","Vehículo")}</div><div class="veh-cap">{int(v.get("capacidad",0)):,}</div><div style="font-size:10px;color:var(--txt3)">tortas/viaje</div><div class="veh-dim">📐 {v.get("ancho_m","?")}×{v.get("largo_m","?")}×{v.get("alto_m","?")} m | Arrume: {v.get("arrume_max","?")}x</div><div class="veh-dim">💵 ${int(v.get("tarifa_km",3000)):,}/km</div></div>',unsafe_allow_html=True)
    st.divider()
    t1,t2 = st.tabs(["✏️  EDITAR","➕  AGREGAR"])
    with t1:
        if not veh_df.empty:
            ved_ = st.selectbox("Vehículo",veh_df["codigo"].tolist(),key="ved")
            rv_ = veh_df[veh_df["codigo"]==ved_].iloc[0]
            c1_,c2_,c3_ = st.columns(3)
            with c1_: nti_=st.text_input("Tipo",str(rv_.get("tipo","Furgoneta")),key="ve_ti"); naw_=st.number_input("Ancho veh (m)",0.1,10.0,float(rv_.get("ancho_m",2.2)),step=0.01,key="ve_aw"); nal_=st.number_input("Largo veh (m)",0.1,20.0,float(rv_.get("largo_m",2.5)),step=0.01,key="ve_al"); nah_=st.number_input("Alto veh (m)",0.1,10.0,float(rv_.get("alto_m",1.8)),step=0.01,key="ve_ah")
            with c2_: nca_=st.number_input("Ancho caja (m)",0.01,2.0,float(rv_.get("caja_ancho",0.30)),step=0.01,key="ve_ca"); ncl_=st.number_input("Largo caja (m)",0.01,2.0,float(rv_.get("caja_largo",0.30)),step=0.01,key="ve_cl"); nch_=st.number_input("Alto caja (m)",0.01,2.0,float(rv_.get("caja_alto",0.15)),step=0.01,key="ve_ch"); nar_=st.number_input("Arrume máx.",1,10,int(rv_.get("arrume_max",3)),key="ve_ar")
            with c3_: ntar_=st.number_input("Tarifa/km ($)",0,100000,int(rv_.get("tarifa_km",3000)),step=100,key="ve_tar"); nest_=st.selectbox("Estado",["Activo","Reserva","En taller","Fuera de servicio"],key="ve_est"); nnot_=st.text_area("Notas",str(rv_.get("notas","") or ""),height=80,key="ve_not"); ncap_=calcular_capacidad(naw_,nal_,nah_,nca_,ncl_,nch_,nar_); st.metric("Capacidad calculada",f"{ncap_:,} tortas")
            ce1_,ce2_ = st.columns(2)
            with ce1_:
                if st.button("💾 Guardar",use_container_width=True,key="ve_save"):
                    try: supabase().table("vehiculos").update({"tipo":nti_,"ancho_m":naw_,"largo_m":nal_,"alto_m":nah_,"caja_ancho":nca_,"caja_largo":ncl_,"caja_alto":nch_,"arrume_max":nar_,"capacidad":ncap_,"tarifa_km":ntar_,"estado":nest_,"notas":nnot_}).eq("codigo",ved_).execute(); alerta("ok",f"<b>{ved_}</b> actualizado."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
            with ce2_:
                if st.button("🗑️ Eliminar",use_container_width=True,key="ve_del"):
                    try: supabase().table("vehiculos").delete().eq("codigo",ved_).execute(); alerta("ok","Eliminado."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
    with t2:
        st.markdown('<div class="dn-form"><div class="dn-form-title">NUEVO VEHÍCULO</div>', unsafe_allow_html=True)
        c1_,c2_,c3_ = st.columns(3)
        with c1_: nvc_=st.text_input("Código",placeholder="TRB-06",key="nv_cod"); nvt_=st.text_input("Tipo",placeholder="Turbo (Plataforma Doble)",key="nv_tipo"); nvaw=st.number_input("Ancho (m)",0.1,10.0,4.0,step=0.01,key="nv_aw"); nval=st.number_input("Largo (m)",0.1,20.0,4.0,step=0.01,key="nv_al"); nvah=st.number_input("Alto (m)",0.1,10.0,2.7,step=0.01,key="nv_ah")
        with c2_: nvca=st.number_input("Ancho caja",0.01,2.0,0.30,step=0.01,key="nv_ca"); nvcl=st.number_input("Largo caja",0.01,2.0,0.30,step=0.01,key="nv_cl"); nvch=st.number_input("Alto caja",0.01,2.0,0.15,step=0.01,key="nv_ch"); nvar=st.number_input("Arrume",1,10,6,key="nv_ar")
        with c3_: nvtar=st.number_input("Tarifa/km",0,100000,6000,step=100,key="nv_tar"); nvest=st.selectbox("Estado",["Activo","Reserva"],key="nv_est"); nvnot=st.text_area("Notas",height=80,key="nv_not"); nvcap=calcular_capacidad(nvaw,nval,nvah,nvca,nvcl,nvch,nvar); st.metric("Capacidad calculada",f"{nvcap:,} tortas")
        if st.button("➕ Agregar",use_container_width=True,key="nv_add"):
            if not nvc_ or not nvt_: alerta("err","Ingresa código y tipo.")
            else:
                try: supabase().table("vehiculos").insert({"codigo":nvc_.strip(),"tipo":nvt_,"ancho_m":nvaw,"largo_m":nval,"alto_m":nvah,"caja_ancho":nvca,"caja_largo":nvcl,"caja_alto":nvch,"arrume_max":nvar,"capacidad":nvcap,"tarifa_km":nvtar,"estado":nvest,"notas":nvnot}).execute(); alerta("ok",f"<b>{nvc_}</b> agregado."); st.rerun()
                except Exception as e: alerta("err",f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── SYS Configuración ─────────────────────────────────────────
elif mod == "SYS" and subpag == "Configuración":
    banner("Configuración del Sistema","Tarifas · Costos · Margen% · Reset","tag-sys","SYS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    t1,t2,t3,t4,t5 = st.tabs(["💵  TARIFAS COBRO","📉  COSTOS OPERATIVOS","📦  ALMACÉN","🍰  PERECEDEROS","🔄  RESET SISTEMA"])
    with t1:
        alerta("info","Cambios en tarifas se reflejan <b>inmediatamente</b> en cotizador, P&G y tabla de rutas.")
        c1_,c2_ = st.columns(2)
        with c1_:
            st.session_state["cfg_tarifa_km"]=st.number_input("Tarifa base/km ($)",0,50000,int(cfg("tarifa_km")),step=100,key="cfg_tk")
            st.session_state["cfg_recargo_nocturno_pct"]=st.number_input("Recargo nocturno (%)",0,100,int(cfg("recargo_nocturno_pct")),key="cfg_rn")
            st.session_state["cfg_tarifa_almacenamiento"]=st.number_input("Almacenamiento ($/ud/día)",0,10000,int(cfg("tarifa_almacenamiento")),step=10,key="cfg_ta")
            st.session_state["cfg_tarifa_alm_ton_dia"]=st.number_input("Almacenamiento ($/ton/día)",0,1000000,int(cfg("tarifa_alm_ton_dia")),step=1000,key="cfg_alm_ton")
        with c2_:
            st.session_state["cfg_tarifa_alistamiento"]=st.number_input("Alistamiento ($/ud)",0,5000,int(cfg("tarifa_alistamiento")),step=10,key="cfg_tali")
            st.session_state["cfg_tarifa_manipulacion"]=st.number_input("Manipulación ($/ud)",0,5000,int(cfg("tarifa_manipulacion")),step=10,key="cfg_tm")
            st.session_state["cfg_tarifa_admin_pct"]=st.number_input("Admin (% flete)",0,50,int(cfg("tarifa_admin_pct")),key="cfg_adm")
            st.session_state["cfg_margen_pct"]=st.slider(f"Margen % (sobre factura total)",0,100,int(cfg("margen_pct")),key="cfg_mg")
        flete_ej=calcular_flete(200,1,True,True)
        _,total_mg_ej=aplicar_margen(flete_ej)
        alerta("ok",f"Ejemplo ruta 200km nocturna: Flete ${flete_ej:,} → <b>Con margen {cfg('margen_pct')}%: ${total_mg_ej:,}</b>")
    with t2:
        alerta("warn","Costos operativos se usan para calcular utilidad neta y P&G real.")
        alerta("info",f"<b>Costos indirectos {cfg('costos_indirectos_pct')}%</b> = depreciación vehículos, seguros, prestaciones sociales conductores (~40% salario), admin CEDI. Se suman al costo directo en P&G.")
        c1_,c2_ = st.columns(2)
        with c1_:
            st.session_state["cfg_costo_combustible_km"]=st.number_input("Combustible ($/km)",0,5000,int(cfg("costo_combustible_km")),step=10,key="cfg_comb")
            st.session_state["cfg_costo_mantenimiento_km"]=st.number_input("Mantenimiento ($/km)",0,1000,int(cfg("costo_mantenimiento_km")),step=5,key="cfg_mant")
            st.session_state["cfg_costos_indirectos_pct"]=st.slider("Costos indirectos (% sobre directo)",0,80,int(cfg("costos_indirectos_pct")),step=5,key="cfg_ind",help="Depreciación, seguros, prestaciones, admin. Valor académico sugerido: 35%")
        with c2_:
            st.session_state["cfg_costo_conductor_dia"]=st.number_input("Conductor ($/día)",0,500000,int(cfg("costo_conductor_dia")),step=5000,key="cfg_cond")
            st.session_state["cfg_costo_peaje_promedio"]=st.number_input("Peajes ($/viaje/veh)",0,100000,int(cfg("costo_peaje_promedio")),step=1000,key="cfg_peaj")
        c_km=cfg("costo_combustible_km")+cfg("costo_mantenimiento_km")
        costo_ej_directo = int(400*1*c_km + cfg("costo_conductor_dia") + cfg("costo_peaje_promedio"))
        costo_ej_total = int(costo_ej_directo*(1+cfg("costos_indirectos_pct")/100))
        alerta("ok",f"Ejemplo ruta 200km: Directo ${costo_ej_directo:,} + Indirectos {cfg('costos_indirectos_pct')}% = <b>Total ${costo_ej_total:,}</b>")
    with t3:
        c1_,c2_ = st.columns(2)
        with c1_: st.session_state["cfg_cap_almacen"]=st.number_input("Cap. máx. (uds)",0,value=int(cfg("cap_almacen")),step=100,key="cfg_ca")
        with c2_: st.session_state["cfg_stock_min"]=st.number_input("Stock mínimo/CEDI",0,99999999,int(cfg("stock_min")),key="cfg_sm")
    with t4:
        c1_,c2_ = st.columns(2)
        with c1_: st.session_state["cfg_vida_util_dias"]=st.number_input("Vida útil (días)",1,30,int(cfg("vida_util_dias")),key="cfg_vu")
        with c2_: st.session_state["cfg_alerta_vence_dias"]=st.number_input("Alerta (días antes)",1,10,int(cfg("alerta_vence_dias")),key="cfg_av")
    with t5:
        alerta("err","⚠️ <b>ZONA DE PELIGRO</b> — El reset borra TODOS los datos operativos: órdenes, pedidos, despachos, movimientos, lotes, almacenamientos y reinicia el stock de CEDIs a 0. <b>NO se borran</b> clientes, vehículos ni rutas.")
        st.markdown("---")
        if not st.session_state.get("reset_paso1",False):
            st.markdown("**Paso 1 de 2:** Confirmar intención de reset")
            if st.button("🗑️ INICIAR RESET DEL SISTEMA",key="reset_p1",use_container_width=True):
                st.session_state.reset_paso1 = True; st.rerun()
        else:
            alerta("warn","⚠️ <b>Último aviso:</b> Esta acción es IRREVERSIBLE. ¿Estás completamente seguro?")
            c_r1,c_r2 = st.columns(2)
            with c_r1:
                st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
                if st.button("✅ SÍ, BORRAR TODO Y REINICIAR",key="reset_p2",use_container_width=True):
                    with st.spinner("Reiniciando sistema..."):
                        reset_sistema()
                    st.session_state.reset_paso1 = False
                    alerta("ok","✅ <b>Sistema reiniciado.</b> Stock en cero. Datos operativos eliminados. Clientes, vehículos y rutas conservados."); st.balloons()
                st.markdown('</div>', unsafe_allow_html=True)
            with c_r2:
                if st.button("❌ Cancelar — Mantener datos",key="reset_cancel",use_container_width=True):
                    st.session_state.reset_paso1 = False; alerta("ok","Reset cancelado. Datos intactos."); st.rerun()
    alerta("ok","Todos los cambios se aplican a toda la sesión actual.")
    st.markdown('</div>', unsafe_allow_html=True)

# ── SYS Especificaciones ──────────────────────────────────────
elif mod == "SYS" and subpag == "Especificaciones":
    banner("Especificaciones Operativas","Parámetros técnicos DistriNova v10","tag-sys","OPS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    veh_df = get_vehiculos(); rutas_df = get_rutas_db()
    vact_ = veh_df[veh_df["estado"]=="Activo"] if not veh_df.empty and "estado" in veh_df.columns else pd.DataFrame()
    k1_,k2_,k3_,k4_ = st.columns(4)
    k1_.metric("Vehículos activos",len(vact_))
    k2_.metric("Cap. flota/viaje",f"{int(vact_['capacidad'].sum()) if not vact_.empty and 'capacidad' in vact_.columns else 0:,}")
    k3_.metric("Rutas activas",len(rutas_df))
    k4_.metric("Cap. almacén",f"{cfg('cap_almacen'):,}")
    t1_,t2_,t3_,t4_ = st.tabs(["🚐  FLOTA","🗺️  RUTAS","💰  TARIFAS","📊  DEMANDA MP"])
    with t1_: st.dataframe(veh_df if not veh_df.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    with t2_:
        if not rutas_df.empty:
            tabla_r = []
            for _,r in rutas_df.iterrows():
                cd = calcular_flete(r["km"],1,False,True); cn = calcular_flete(r["km"],1,True,True)
                _,cd_m = aplicar_margen(cd); _,cn_m = aplicar_margen(cn)
                tabla_r.append({"Municipio":r["municipio"],"KM":r["km"],"KM i/v":float(r["km"])*2,"Flete diurno":f"${cd:,}","Noc c/margen":f"${cn_m:,}","Salida máx":r.get("salida_max","—"),"Activa":r.get("activa",True)})
            st.dataframe(pd.DataFrame(tabla_r),use_container_width=True,hide_index=True)
        else: alerta("info","Sin rutas.")
    with t3_:
        st.markdown(f"| Servicio | Tarifa |\n|---|---|\n| Transporte | ${cfg('tarifa_km'):,}/km |\n| Nocturno | +{cfg('recargo_nocturno_pct')}% |\n| Margen | +{cfg('margen_pct')}% sobre total |\n| Almacenamiento | ${cfg('tarifa_alm_ton_dia'):,}/ton/día |\n| Alistamiento | ${cfg('tarifa_alistamiento'):,}/ud |\n| Manipulación | ${cfg('tarifa_manipulacion'):,}/ud |\n| Admin | {cfg('tarifa_admin_pct')}% del flete |")
    with t4_:
        alerta("info","Demanda estimada del fabricante. El proveedor debe tener <b>más</b> de estas cantidades disponibles para cubrir la demanda mensual.")
        st.dataframe(pd.DataFrame({
            "Material":["Harina","Azúcar","Mantequilla","Huevos (past.)","Leche","Almendras","Pasas"],
            "Pedido diario (500 tortas)":["100 kg","80 kg","50 kg (est.)","50 kg (est.)","30 L (est.)","12 kg (est.)","12 kg (est.)"],
            "Pedido semanal (2,500 tortas)":["500 kg","400 kg","250 kg","250 kg","150 L","60 kg","60 kg"],
            "Pedido mensual estimado":["~2,000 kg","~1,600 kg","~1,000 kg","~1,000 kg","~600 L","~240 kg","~240 kg"],
        }),use_container_width=True,hide_index=True)
        alerta("warn","El proveedor mencionó <b>~4 T mensuales</b> de materia prima total. DistriNova debe tener capacidad de almacenamiento para al menos 5-6 T (50% extra de seguridad).")
    st.markdown('</div>', unsafe_allow_html=True)

# ── SYS Equipo ────────────────────────────────────────────────
elif mod == "SYS" and subpag == "Equipo":
    banner("Equipo Operativo","Roles y responsabilidades DistriNova","tag-sys","RH")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    eq_ = [("👑","Yoany","COO · Director Operaciones","#1E88E5","KPIs · Junta · Estrategia","WMS·TMS·FIN·SYS·IA"),
           ("🗺️","Gómez","Coord. Logística y Tráfico","#FF8C00","Rutas · Nocturnos · Flota","TMS"),
           ("📦","Karen","Analista Inventarios","#00C97A","Stock · Perecederos FIFO · Almacenamiento","WMS·CLI"),
           ("🚛","Laura","Auxiliar Operaciones","#FFB800","Cargue · Estiba · Verificación","WMS·TMS"),
           ("🧾","Mafe","Facturación y Documentación","#42A5F5","Facturas · Remisiones · Pedidos","FIN")]
    cols_ = st.columns(3)
    for i,(em,nom,cargo,color,resp,mods) in enumerate(eq_):
        with cols_[i%3]:
            st.markdown(f'<div class="dn-section" style="margin-bottom:10px"><div style="display:flex;align-items:center;gap:14px;padding:14px 18px"><div style="font-size:28px">{em}</div><div style="flex:1"><div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:{color}">{cargo}</div><div style="font-family:var(--cond);font-size:18px;font-weight:700;color:white">{nom}</div><div style="font-size:11px;color:var(--txt2);margin-top:2px">{resp}</div></div><div style="font-size:10px;color:{color};font-weight:600">{mods}</div></div></div>',unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── IA Asistente ──────────────────────────────────────────────
elif mod == "IA" and subpag == "Asistente":
    banner("NOVA — Asistente IA","Inteligencia artificial con acceso al estado real de la operación","tag-ia","IA")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    ia_ok = any([get_ia_key("gemini"),get_ia_key("anthropic"),get_ia_key("openai")])
    if not ia_ok:
        alerta("warn","⚙️ <b>NOVA requiere configuración.</b> Agrega en <code>.streamlit/secrets.toml</code>:<br><code>GEMINI_API_KEY = \"AIza...\"</code> — Obtén tu key GRATIS en <b>aistudio.google.com</b>")
    else:
        alerta("ia","◈ <b>NOVA</b> activa · Acceso en tiempo real: stock, rutas, clientes, flota, costos, P&G.")
    sugs = ["¿Cuál es el estado actual del inventario?","¿Cuántos vehículos necesito para 1,500 tortas hoy?","¿Qué ruta tiene mejor margen de rentabilidad?","¿Hay lotes próximos a vencer?","Genera reporte ejecutivo para la Junta Directiva","¿Cuánto cuesta almacenar 2 toneladas de harina 30 días?","¿Cuál es la capacidad total de la flota de turbos?","Dame el costo total de almacenamiento activo"]
    sc1_,sc2_ = st.columns(2)
    for i,sg in enumerate(sugs):
        with [sc1_,sc2_][i%2]:
            if st.button(sg,key=f"sug_{i}",use_container_width=True):
                save_msg("user",sg)
                with st.spinner("◈ NOVA analizando..."): resp=call_nova(st.session_state.ia_msgs[:-1],sg)
                save_msg("assistant",resp); st.rerun()
    if st.session_state.ia_msgs:
        st.markdown(f'<div class="dn-section"><div class="dn-section-header"><span>CONVERSACIÓN</span><span style="color:var(--txt3)">{len(st.session_state.ia_msgs)} mensajes</span></div><div class="dn-section-body" style="max-height:420px;overflow-y:auto">',unsafe_allow_html=True)
        for msg in st.session_state.ia_msgs: render_msg(msg)
        st.markdown('</div></div>',unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;padding:40px;color:var(--txt3)"><div style="font-size:40px">◈</div><div style="font-family:var(--cond);font-size:18px;margin-top:12px">NOVA lista</div></div>',unsafe_allow_html=True)
    ci_,cb_ = st.columns([5,1])
    with ci_: user_input=st.text_input("Pregunta",placeholder="Escribe tu pregunta...",label_visibility="collapsed",key="ia_inp")
    with cb_: send_=st.button("Enviar ▶",use_container_width=True,key="ia_send")
    if send_ and user_input.strip():
        save_msg("user",user_input)
        with st.spinner("◈ NOVA analizando..."): resp=call_nova(st.session_state.ia_msgs[:-1],user_input)
        save_msg("assistant",resp); st.rerun()
    if st.button("🗑️ Limpiar chat",key="ia_clear"): st.session_state.ia_msgs=[]; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── IA Análisis ───────────────────────────────────────────────
elif mod == "IA" and subpag == "Análisis":
    banner("Análisis Automático de KPIs","NOVA genera reportes inteligentes con datos reales","tag-ia","KPI")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    reportes_ = {
        "📊 Reporte ejecutivo — Junta Directiva":"Genera un reporte ejecutivo formal para la Junta Directiva de DistriNova v10. Incluye: estado del inventario por CEDI, clientes activos, almacenamientos, desempeño operativo, ingresos, utilidad estimada, alertas críticas y 3 recomendaciones estratégicas.",
        "🚐 Optimización de flota":"Analiza la flota completa (furgonetas + turbos). ¿Cuándo conviene usar un turbo vs furgoneta? ¿Cuál es la combinación óptima para distintos volúmenes? Dame recomendaciones concretas.",
        "💵 Análisis de rentabilidad por ruta":"Compara todas las rutas con margen incluido: ingreso total, costo operativo, utilidad neta. ¿Cuál ruta es más rentable? ¿Alguna no cubre costos?",
        "🍰 Alerta de perecederos":"Revisa los lotes activos. Identifica riesgos de vencimiento y qué despachar prioritariamente hoy.",
        "🏭 Estado CEDIs y cadena completa":"Analiza stock por CEDI. ¿Riesgo de ruptura? ¿Qué transferencias recomiendas? ¿La cadena proveedor→fabricante→mayorista→minorista está balanceada?",
        "💰 Análisis de almacenamiento":"¿Cuánto estamos cobrando por almacenamiento? ¿Es rentable vs los costos de mantener el CEDI? ¿Qué clientes generan más ingresos de almacenamiento?"
    }
    c1_,c2_ = st.columns(2)
    for i,(nombre,prompt) in enumerate(reportes_.items()):
        with [c1_,c2_][i%2]:
            if st.button(nombre,key=f"rep_{i}",use_container_width=True):
                with st.spinner("◈ NOVA generando reporte..."): resp=call_nova([],prompt)
                st.session_state["rep_nombre"]=nombre; st.session_state["rep_result"]=resp; st.rerun()
    if "rep_result" in st.session_state:
        txt = re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',st.session_state["rep_result"]).replace("\n","<br>")
        st.markdown(f'<div class="dn-section"><div class="dn-section-header"><span>◈ {st.session_state.get("rep_nombre","REPORTE")}</span><span style="color:var(--txt3)">NOVA</span></div><div class="dn-section-body" style="line-height:1.7;font-size:13px">{txt}</div></div>',unsafe_allow_html=True)
        if st.button("🗑️ Limpiar",key="rep_clear"): del st.session_state["rep_result"]; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
