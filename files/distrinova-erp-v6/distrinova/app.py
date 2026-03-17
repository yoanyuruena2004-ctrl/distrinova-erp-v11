"""
DistriNova ERP v6.0
Módulos: WMS · TMS · FIN · SYS · IA
Nuevas funciones: Rutas dinámicas, Flota editable, Agente IA
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database import supabase
from datetime import datetime, date, timedelta
import requests, json, math

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_OK = True
except ImportError:
    FOLIUM_OK = False

# ══════════════════════════════════════════════════════
# PÁGINA
# ══════════════════════════════════════════════════════
st.set_page_config(page_title="DistriNova ERP", page_icon="🚚",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&family=Barlow+Condensed:wght@600;700;800&display=swap');
:root{--bg:#060D18;--bg2:#0C1829;--bg3:#111F33;--bg4:#16263D;--border:rgba(255,255,255,.07);--border2:rgba(30,136,229,.2);--txt:#C8D8EA;--txt2:#5A7A99;--txt3:#334D66;--accent:#1E88E5;--accent2:#FF8C00;--green:#00C97A;--red:#FF4444;--yellow:#FFB800;--purple:#9C6FE4;--font:'Space Grotesk',sans-serif;--mono:'JetBrains Mono',monospace;--cond:'Barlow Condensed',sans-serif}
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
.stTabs [data-baseweb="tab-list"]{background:var(--bg2)!important;border-bottom:1px solid var(--border)!important;padding:0 4px!important;gap:0!important}
.stTabs [data-baseweb="tab"]{color:var(--txt2)!important;font-size:11px!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:1px!important;padding:12px 18px!important;border-bottom:2px solid transparent!important;background:transparent!important}
.stTabs [aria-selected="true"]{color:var(--txt)!important;border-bottom-color:var(--accent2)!important}
.stProgress>div>div{background:linear-gradient(90deg,var(--accent),#42A5F5)!important;border-radius:4px!important}
.stProgress>div{background:var(--bg4)!important;border-radius:4px!important;height:6px!important}
.stSelectbox>div>div,.stNumberInput>div>div,.stTextInput>div>div,.stTextArea>div>div{background:var(--bg3)!important;border:1px solid var(--border)!important;border-radius:8px!important;color:var(--txt)!important}
.stSelectbox label,.stNumberInput label,.stTextInput label,.stTextArea label,.stCheckbox label,.stDateInput label{color:var(--txt2)!important;font-size:11px!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:1px!important}
hr{border-color:var(--border)!important;margin:20px 0!important}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:var(--bg2)}
::-webkit-scrollbar-thumb{background:var(--bg4);border-radius:4px}

/* ── Componentes DistriNova ── */
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
.dn-user{padding:14px 18px;border-top:1px solid var(--border);display:flex;align-items:center;gap:10px}
.dn-avatar{width:32px;height:32px;border-radius:50%;background:var(--bg4);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.dn-user-name{font-size:13px;font-weight:600;color:var(--txt)}
.dn-user-role{font-size:10px;color:var(--txt3)}

/* ── Chat IA ── */
.ia-bubble-user{background:var(--bg4);border:1px solid var(--border);border-radius:12px 12px 4px 12px;padding:12px 16px;margin:8px 0 8px 40px;font-size:13px;color:var(--txt);line-height:1.5}
.ia-bubble-bot{background:rgba(156,111,228,.08);border:1px solid rgba(156,111,228,.2);border-radius:12px 12px 12px 4px;padding:12px 16px;margin:8px 40px 8px 0;font-size:13px;color:var(--txt);line-height:1.6}
.ia-bubble-bot b{color:#CE93D8}
.ia-name-user{font-size:10px;color:var(--txt3);text-align:right;margin-right:4px;text-transform:uppercase;letter-spacing:1px}
.ia-name-bot{font-size:10px;color:rgba(156,111,228,.6);margin-left:4px;text-transform:uppercase;letter-spacing:1px}
.ia-thinking{color:rgba(156,111,228,.5);font-size:12px;font-style:italic;padding:8px 16px}

/* ── Vehículo card ── */
.veh-card{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:16px;transition:all .2s;position:relative}
.veh-card:hover{border-color:var(--border2)}
.veh-codigo{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--accent2);margin-bottom:6px}
.veh-tipo{font-family:var(--cond);font-size:18px;font-weight:700;color:white;margin-bottom:8px}
.veh-cap{font-family:var(--mono);font-size:26px;font-weight:700;color:var(--accent)}
.veh-dim{font-size:11px;color:var(--txt2);margin-top:3px}
.veh-status{position:absolute;top:14px;right:14px}

/* ── Ruta card ── */
.ruta-row{display:grid;grid-template-columns:1.4fr 70px 80px 100px 110px 80px 60px;border-bottom:1px solid var(--border);font-size:12px}
.ruta-row:last-child{border-bottom:none}
.ruta-row>div{padding:10px 14px;display:flex;align-items:center}
.ruta-row.hdr>div{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--txt3);padding:9px 14px;background:var(--bg4)}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# DEFAULTS CONFIGURABLES
# ══════════════════════════════════════════════════════
DEFAULTS = {
    "tarifa_km":3000,"recargo_nocturno_pct":30,
    "tarifa_almacenamiento":500,"tarifa_alistamiento":200,
    "tarifa_manipulacion":150,"tarifa_admin_pct":5,
    "cap_almacen":5000,"stock_min":50,
    "vida_util_dias":3,"alerta_vence_dias":2,
    "caja_ancho":0.30,"caja_largo":0.30,"caja_alto":0.15,
}
for k,v in DEFAULTS.items():
    if f"cfg_{k}" not in st.session_state: st.session_state[f"cfg_{k}"] = v

def cfg(k): return st.session_state.get(f"cfg_{k}", DEFAULTS.get(k,0))

CEDIS = ["Medellín","Santa Rosa","Taraza"]

# ══════════════════════════════════════════════════════
# BASE DE DATOS
# ══════════════════════════════════════════════════════
def db_get(tabla, order="created_at", desc=True, limit=300):
    try:
        q = supabase().table(tabla).select("*")
        if order: q = q.order(order, desc=desc)
        if limit: q = q.limit(limit)
        r = q.execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except: return pd.DataFrame()

def get_inv():      return db_get("inventario", order="cedi", desc=False)
def get_desp():     return db_get("despachos")
def get_ped():      return db_get("pedidos")
def get_mov():      return db_get("movimientos", limit=50)
def get_lotes():    return db_get("lotes", order="fecha_vencimiento", desc=False)

def get_rutas_db():
    df = db_get("rutas", order="km", desc=False)
    if df.empty:
        # fallback si la tabla aún no existe
        return pd.DataFrame([
            {"id":1,"municipio":"Santa Rosa de Osos","km":77.4,"tiempo_est":"1h 20m","salida_max":"03:40","lat":6.6458,"lon":-75.4627,"activa":True},
            {"id":2,"municipio":"Yarumal","km":122.4,"tiempo_est":"2h 10m","salida_max":"02:50","lat":7.0025,"lon":-75.5147,"activa":True},
            {"id":3,"municipio":"Valdivia","km":174.0,"tiempo_est":"3h 00m","salida_max":"02:00","lat":7.1692,"lon":-75.4397,"activa":True},
            {"id":4,"municipio":"Taraza","km":249.0,"tiempo_est":"4h 10m","salida_max":"00:50","lat":7.5731,"lon":-75.4058,"activa":True},
            {"id":5,"municipio":"Caucasia","km":283.0,"tiempo_est":"4h 45m","salida_max":"00:15","lat":7.9887,"lon":-75.1973,"activa":True},
        ])
    return df

def get_vehiculos():
    df = db_get("vehiculos", order="codigo", desc=False)
    if df.empty:
        return pd.DataFrame([
            {"id":1,"codigo":"FRG-01","tipo":"Furgoneta","ancho_m":2.2,"largo_m":2.5,"alto_m":1.8,"arrume_max":3,"capacidad":168,"tarifa_km":3000,"estado":"Activo"},
            {"id":2,"codigo":"FRG-02","tipo":"Furgoneta","ancho_m":2.2,"largo_m":2.5,"alto_m":1.8,"arrume_max":3,"capacidad":168,"tarifa_km":3000,"estado":"Activo"},
            {"id":3,"codigo":"FRG-03","tipo":"Furgoneta","ancho_m":2.2,"largo_m":2.5,"alto_m":1.8,"arrume_max":3,"capacidad":168,"tarifa_km":3000,"estado":"Activo"},
            {"id":4,"codigo":"FRG-04","tipo":"Furgoneta","ancho_m":2.2,"largo_m":2.5,"alto_m":1.8,"arrume_max":3,"capacidad":168,"tarifa_km":3000,"estado":"Reserva"},
        ])
    return df

def get_chat_hist(n=20):
    return db_get("ia_chat", order="created_at", desc=False, limit=n)

def stock_cedi(df, nom):
    r = df.loc[df["cedi"]==nom,"stock"]
    return int(r.values[0]) if len(r)>0 else 0

def stock_total(df): return int(df["stock"].sum()) if not df.empty else 0

def calcular_capacidad(ancho_v, largo_v, alto_v, caja_a, caja_l, caja_al, arrume):
    """Cubicaje: cuántas cajas caben en la furgoneta."""
    if caja_a <= 0 or caja_l <= 0 or caja_al <= 0: return 0
    cols = int(ancho_v / caja_a)
    filas = int(largo_v / caja_l)
    niveles = min(int(alto_v / caja_al), arrume)
    return cols * filas * niveles

# ══════════════════════════════════════════════════════
# NAVEGACIÓN
# ══════════════════════════════════════════════════════
if "modulo"  not in st.session_state: st.session_state.modulo  = "WMS"
if "subpag"  not in st.session_state: st.session_state.subpag  = "Dashboard"
if "usuario" not in st.session_state: st.session_state.usuario = "Yoany"
if "ia_msgs" not in st.session_state: st.session_state.ia_msgs = []

MODULOS = {
    "WMS":{"icon":"📦","full":"Almacén",   "color":"#1E88E5","tag":"tag-wms",
           "subs":[("📊","Dashboard","Panel general"),("🏭","Inventario","Stock CEDI"),("🍰","Perecederos","Control FIFO")]},
    "TMS":{"icon":"🚐","full":"Transporte","color":"#FF8C00","tag":"tag-tms",
           "subs":[("🗺️","Rutas","Planeador"),("🏙️","Gestión Rutas","Agregar/editar rutas"),("📍","Mapa","Vista geográfica"),("🛒","Pedidos","Órdenes")]},
    "FIN":{"icon":"💵","full":"Finanzas",  "color":"#00C97A","tag":"tag-fin",
           "subs":[("💵","Cotizador","Tarifas logísticas"),("📄","Documentos","Remisiones · Facturas"),("📋","Historial","Registros")]},
    "SYS":{"icon":"⚙️","full":"Sistema",  "color":"#5A7A99","tag":"tag-sys",
           "subs":[("🚐","Flota","Gestión vehículos"),("🔧","Configuración","Tarifas · parámetros"),("⚙️","Especificaciones","Datos técnicos"),("👥","Equipo","Roles")]},
    "IA" :{"icon":"🤖","full":"Asistente IA","color":"#9C6FE4","tag":"tag-ia",
           "subs":[("🤖","Asistente","Chat operativo"),("📈","Análisis","Reportes KPI automáticos")]},
}

USUARIOS = {
    "Yoany":{"rol":"COO","icon":"👑"},
    "Gómez":{"rol":"Logística","icon":"🗺️"},
    "Karen":{"rol":"Inventarios","icon":"📦"},
    "Laura":{"rol":"Operaciones","icon":"🚛"},
    "Mafe": {"rol":"Documentación","icon":"🧾"},
}

# ══════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════
with st.sidebar:
    now = datetime.now()
    st.markdown(f"""
    <div class="dn-logo">
        <div class="dn-logo-title">DISTRI<span>NOVA</span></div>
        <div class="dn-logo-sub">Operador Logístico · Norte Antioquia</div>
        <div class="dn-badge">● v6.0 &nbsp;{now.strftime('%H:%M')}</div>
    </div>""", unsafe_allow_html=True)

    for mod_key, mod in MODULOS.items():
        ia_color = "rgba(156,111,228,.4)" if mod_key=="IA" else "var(--txt3)"
        st.markdown(f'<div class="dn-mod-hdr" style="color:{ia_color}">{mod["icon"]} &nbsp;{mod["full"]}</div>', unsafe_allow_html=True)
        for si, sn, sd in mod["subs"]:
            if st.button(f"{si}  {sn}", key=f"nav_{mod_key}_{sn}", use_container_width=True, help=sd):
                st.session_state.modulo = mod_key
                st.session_state.subpag = sn
                st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.divider()
    usr_key = st.selectbox("", list(USUARIOS.keys()),
        index=list(USUARIOS.keys()).index(st.session_state.usuario),
        key="usr_sel", label_visibility="collapsed")
    st.session_state.usuario = usr_key
    usr_info = USUARIOS[usr_key]
    st.markdown(f"""
    <div class="dn-user">
        <div class="dn-avatar">{usr_info['icon']}</div>
        <div><div class="dn-user-name">{usr_key}</div><div class="dn-user-role">{usr_info['rol']}</div></div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════
mod      = st.session_state.modulo
subpag   = st.session_state.subpag
mod_info = MODULOS[mod]
usr_name = st.session_state.usuario

def alerta(tipo, txt):
    cls={"ok":"dn-ok","warn":"dn-warn","err":"dn-err","info":"dn-info","ia":"dn-ia"}
    ic ={"ok":"●","warn":"▲","err":"✕","info":"ℹ","ia":"◈"}
    st.markdown(f'<div class="dn-alert {cls[tipo]}">{ic[tipo]} {txt}</div>', unsafe_allow_html=True)

def module_banner(titulo, sub, tag, label=""):
    st.markdown(f"""
    <div class="dn-module-banner" data-label="{label}">
        <div class="dn-module-tag {tag}">{mod_info['icon']} {mod_info['full']}</div>
        <div style="font-family:var(--cond);font-size:28px;font-weight:800;color:white;letter-spacing:.5px;margin-bottom:3px">{titulo}</div>
        <div style="font-size:12px;color:var(--txt2)">{sub}</div>
    </div>""", unsafe_allow_html=True)

def mini_chart(labels, vals, color, height=180):
    fig = go.Figure(go.Bar(x=labels, y=vals, marker=dict(color=color,opacity=.85),
        text=[f"{v:,}" for v in vals], textposition="outside",
        textfont=dict(color="rgba(200,216,234,.7)",size=11)))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=22,b=4,l=4,r=4),height=height,
        xaxis=dict(showgrid=False,tickfont=dict(size=11,color="#5A7A99")),
        yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.04)",tickfont=dict(size=10,color="#5A7A99")))
    return fig

def gauge(val, mx, titulo):
    pct=val/mx if mx else 0
    c="#00C97A" if pct<.6 else "#FFB800" if pct<.85 else "#FF4444"
    fig=go.Figure(go.Indicator(mode="gauge+number",value=val,
        title={"text":titulo,"font":{"color":"#5A7A99","size":10,"family":"Space Grotesk"}},
        number={"font":{"color":"#C8D8EA","size":22,"family":"JetBrains Mono"}},
        gauge={"axis":{"range":[0,mx],"tickcolor":"#334D66","tickfont":{"size":8}},"bar":{"color":c,"thickness":.55},
               "bgcolor":"#16263D","bordercolor":"rgba(255,255,255,.07)",
               "steps":[{"range":[0,mx*.6],"color":"rgba(0,201,122,.04)"},{"range":[mx*.6,mx*.85],"color":"rgba(255,184,0,.04)"},{"range":[mx*.85,mx],"color":"rgba(255,68,68,.05)"}]}))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",margin=dict(t=36,b=8,l=16,r=16),height=175)
    return fig

# ══════════════════════════════════════════════════════════════
# AGENTE IA — construye contexto y llama Claude API
# ══════════════════════════════════════════════════════════════
def build_context():
    """Recopila el estado actual del ERP para dárselo al agente."""
    inv_df   = get_inv()
    desp_df  = get_desp()
    lotes_df = get_lotes()
    veh_df   = get_vehiculos()
    rutas_df = get_rutas_db()
    ped_df   = get_ped()

    stk = stock_total(inv_df)
    uso = round(stk / cfg("cap_almacen") * 100, 1)
    fletes_total = int(desp_df["costo_flete"].sum()) if not desp_df.empty else 0
    tortas_t = int(desp_df["tortas"].sum()) if not desp_df.empty else 0
    veh_activos = len(veh_df[veh_df["estado"]=="Activo"]) if not veh_df.empty else 4
    cap_total_flota = int(veh_df[veh_df["estado"]=="Activo"]["capacidad"].sum()) if not veh_df.empty else 672

    lotes_criticos = []
    if not lotes_df.empty and "fecha_vencimiento" in lotes_df.columns:
        hoy = date.today()
        lotes_df["fv"] = pd.to_datetime(lotes_df["fecha_vencimiento"]).dt.date
        for _, l in lotes_df.iterrows():
            dias = (l["fv"] - hoy).days
            if dias <= cfg("alerta_vence_dias"):
                lotes_criticos.append(f"{l.get('lote_id','?')} ({l.get('cedi','?')}): {l.get('cantidad',0)} uds, {'VENCIDO' if dias<0 else f'vence en {dias}d'}")

    stock_por_cedi = {}
    if not inv_df.empty:
        for _, r in inv_df.iterrows():
            stock_por_cedi[r["cedi"]] = r["stock"]

    rutas_list = []
    if not rutas_df.empty:
        for _, r in rutas_df[rutas_df.get("activa", pd.Series([True]*len(rutas_df)))].iterrows():
            fl_n = int(r["km"] * cfg("tarifa_km") * (1+cfg("recargo_nocturno_pct")/100))
            rutas_list.append(f"  - {r['municipio']}: {r['km']} km, salida máx {r.get('salida_max','—')}, flete noc 1 furg: ${fl_n:,}")

    pedidos_pendientes = len(ped_df) if not ped_df.empty else 0

    ctx = f"""
Eres NOVA, el asistente de inteligencia artificial de DistriNova ERP — operador logístico especializado en distribución de tortas caseras al norte de Antioquia, Colombia.

ESTADO ACTUAL DEL SISTEMA ({datetime.now().strftime('%d/%m/%Y %H:%M')}):

INVENTARIO:
- Stock total: {stk:,} unidades ({uso}% del almacén de {cfg('cap_almacen'):,})
- Por CEDI: {stock_por_cedi}
- Stock mínimo configurado: {cfg('stock_min')} unidades/CEDI

FLOTA:
- Vehículos activos: {veh_activos}
- Capacidad total flota activa: {cap_total_flota:,} unidades/viaje
- Para 500 tortas: {math.ceil(500/max(cap_total_flota//max(veh_activos,1),1))} vehículos min.

OPERACIONES:
- Despachos registrados: {len(desp_df)}
- Tortas movilizadas: {tortas_t:,}
- Ingresos por fletes: ${fletes_total:,}
- Pedidos pendientes: {pedidos_pendientes}

TARIFAS VIGENTES:
- Transporte: ${cfg('tarifa_km'):,}/km + {cfg('recargo_nocturno_pct')}% nocturno
- Almacenamiento: ${cfg('tarifa_almacenamiento'):,}/ud/día
- Alistamiento: ${cfg('tarifa_alistamiento'):,}/ud
- Manipulación: ${cfg('tarifa_manipulacion'):,}/ud
- Admin: {cfg('tarifa_admin_pct')}% sobre flete

RUTAS ACTIVAS:
{chr(10).join(rutas_list) if rutas_list else '  No hay rutas cargadas'}

PERECEDEROS:
- Vida útil: {cfg('vida_util_dias')} días
- Lotes críticos: {lotes_criticos if lotes_criticos else 'Ninguno'}

EQUIPO:
- Yoany (COO), Gómez (Logística), Karen (Inventarios), Laura (Operaciones), Mafe (Documentación)
- Usuario activo ahora: {usr_name}

RESTRICCIÓN OPERATIVA CRÍTICA: Todas las entregas deben llegar ANTES de las 5:00 AM.

Responde SIEMPRE en español. Sé preciso, usa los datos reales del sistema.
Cuando calcules fletes usa las tarifas vigentes. Cuando recomiendes, justifica con los datos.
Formato: usa negritas (**texto**) para valores importantes. Sé conciso pero completo.
Si detectas problemas operativos críticos, menciónalos primero.
"""
    return ctx

def call_claude(messages_hist, user_msg):
    """Llama a la API de Claude con el contexto del ERP."""
    system_ctx = build_context()
    msgs = [{"role": m["rol"], "content": m["mensaje"]} for m in messages_hist[-12:]]
    msgs.append({"role": "user", "content": user_msg})
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": system_ctx,
                "messages": msgs,
            },
            timeout=30
        )
        data = resp.json()
        if "content" in data and data["content"]:
            return data["content"][0]["text"]
        return f"Error en la respuesta: {data.get('error', {}).get('message', 'desconocido')}"
    except Exception as e:
        return f"No se pudo conectar con el agente: {e}"

def save_msg(rol, msg):
    """Guarda en session_state y opcionalmente en Supabase."""
    st.session_state.ia_msgs.append({"rol": rol, "mensaje": msg, "ts": datetime.now().strftime("%H:%M")})
    try:
        supabase().table("ia_chat").insert({"usuario": usr_name, "rol": rol, "mensaje": msg}).execute()
    except: pass

def render_msg(msg):
    if msg["rol"] == "user":
        st.markdown(f'<div class="ia-name-user">{usr_name}</div><div class="ia-bubble-user">{msg["mensaje"]}</div>', unsafe_allow_html=True)
    else:
        txt = msg["mensaje"].replace("**","<b>",1)
        # reemplazar pares de ** de forma simple
        import re
        txt = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', msg["mensaje"])
        st.markdown(f'<div class="ia-name-bot">◈ NOVA · {msg.get("ts","")}</div><div class="ia-bubble-bot">{txt}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# PÁGINAS
# ══════════════════════════════════════════════════════

# ── WMS: Dashboard ──────────────────────────────────
if mod=="WMS" and subpag=="Dashboard":
    module_banner("Panel de Control","Operación en tiempo real · Norte de Antioquia","tag-wms","WMS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)

    inv_df=get_inv(); desp_df=get_desp(); lotes_df=get_lotes()
    stk=stock_total(inv_df); uso=round(stk/cfg("cap_almacen")*100,1)
    fletes=int(desp_df["costo_flete"].sum()) if not desp_df.empty else 0
    tortas_t=int(desp_df["tortas"].sum()) if not desp_df.empty else 0

    k1,k2,k3,k4=st.columns(4)
    k1.metric("Stock Total",f"{stk:,}",f"{uso}% almacén")
    k2.metric("Viajes",len(desp_df))
    k3.metric("Ingresos Fletes",f"${fletes:,}")
    k4.metric("Tortas Movilizadas",f"{tortas_t:,}")
    k5,k6,k7,k8=st.columns(4)
    k5.metric("Cap. Almacén",f"{cfg('cap_almacen'):,}",f"{cfg('cap_almacen')-stk:,} libres")
    k6.metric("Ingreso/Unidad",f"${fletes//tortas_t:,}" if tortas_t else "—")
    k7.metric("Furg. 500/día",f"{math.ceil(500/168)}")
    k8.metric("Furg. 600/día",f"{math.ceil(600/168)}")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Alertas
    alts=[]
    if not inv_df.empty:
        for _,row in inv_df.iterrows():
            if row["stock"]<=cfg("stock_min"): alts.append(("err",f"<b>RUPTURA — CEDI {row['cedi']}:</b> {row['stock']} uds. Emitir OC urgente."))
            elif row["stock"]<=cfg("stock_min")*2: alts.append(("warn",f"Stock bajo CEDI {row['cedi']}: {row['stock']} uds."))
    if uso>85: alts.append(("err",f"<b>Almacén al {uso}%:</b> {cfg('cap_almacen')-stk:,} espacios."))
    elif uso>65: alts.append(("warn",f"Almacén al {uso}%."))
    if not lotes_df.empty and "fecha_vencimiento" in lotes_df.columns:
        hoy=date.today()
        lotes_df["fv"]=pd.to_datetime(lotes_df["fecha_vencimiento"]).dt.date
        for _,l in lotes_df.iterrows():
            dias=(l["fv"]-hoy).days
            if dias<=cfg("alerta_vence_dias"):
                alts.append(("err" if dias<=0 else "warn",f"Lote {l.get('lote_id','?')} ({l.get('cedi','?')}): {l.get('cantidad',0)} tortas {'VENCIDAS' if dias<0 else 'hoy' if dias==0 else f'vencen en {dias}d'}."))
    if not alts: alts.append(("ok","Todos los indicadores operativos dentro de parámetros normales."))

    ca,cb=st.columns([3,2])
    with ca:
        st.markdown('<div class="dn-section"><div class="dn-section-header">ALERTAS OPERATIVAS</div><div class="dn-section-body">', unsafe_allow_html=True)
        for t,tx in alts: alerta(t,tx)
        st.markdown('</div></div>', unsafe_allow_html=True)
    with cb:
        st.plotly_chart(gauge(stk,cfg("cap_almacen"),f"ALMACÉN {uso}%"),use_container_width=True)

    gc1,gc2=st.columns(2)
    with gc1:
        st.markdown('<div class="dn-section"><div class="dn-section-header">STOCK POR CEDI</div><div class="dn-section-body">', unsafe_allow_html=True)
        if not inv_df.empty: st.plotly_chart(mini_chart(inv_df["cedi"].tolist(),inv_df["stock"].tolist(),"#1E88E5"),use_container_width=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    with gc2:
        st.markdown('<div class="dn-section"><div class="dn-section-header">TORTAS POR DESTINO</div><div class="dn-section-body">', unsafe_allow_html=True)
        if not desp_df.empty and "destino" in desp_df.columns:
            grp=desp_df.groupby("destino")["tortas"].sum().reset_index()
            st.plotly_chart(mini_chart(grp["destino"].tolist(),grp["tortas"].tolist(),"#FF8C00"),use_container_width=True)
        else: st.caption("Sin despachos.")
        st.markdown('</div></div>', unsafe_allow_html=True)

    # CEDIs
    cc1,cc2,cc3=st.columns(3)
    for col,nom,rol,color in [(cc1,"Medellín","Principal","#1E88E5"),(cc2,"Santa Rosa","Distribución","#FF8C00"),(cc3,"Taraza","Distribución","#00C97A")]:
        sk=stock_cedi(inv_df,nom); pct=min(1.0,sk/(cfg("stock_min")*4))
        est="err" if sk<=cfg("stock_min") else "warn" if sk<=cfg("stock_min")*2 else "ok"
        est_lbl="CRÍTICO" if est=="err" else "BAJO" if est=="warn" else "NORMAL"
        est_c="status-err" if est=="err" else "status-warn" if est=="warn" else "status-ok"
        bar_c="#FF4444" if est=="err" else "#FFB800" if est=="warn" else "#00C97A"
        with col:
            st.markdown(f"""<div class="dn-cedi"><div class="dn-cedi-tag">CEDI · {rol}</div>
            <div class="dn-cedi-name">{nom}</div><div style="margin-top:5px"><span class="dn-status {est_c}">{est_lbl}</span></div>
            <div class="dn-cedi-stock">{sk:,}</div><div style="font-size:10px;color:var(--txt3)">unidades en stock</div>
            <div class="dn-cedi-bar"><div class="dn-cedi-fill" style="width:{pct*100:.0f}%;background:{bar_c}"></div></div>
            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--txt3);margin-top:5px">
            <span>Mín:{cfg('stock_min')}</span><span>Cap:{cfg('cap_almacen'):,}</span></div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="dn-section"><div class="dn-section-header"><span>ÚLTIMOS DESPACHOS</span><span style="color:var(--txt3);font-size:10px">Top 6</span></div><div class="dn-section-body">', unsafe_allow_html=True)
    if not desp_df.empty:
        ok=[c for c in ["remision","cedi_origen","destino","tortas","furgonetas","costo_flete","nocturno","created_at"] if c in desp_df.columns]
        st.dataframe(desp_df[ok].head(6).rename(columns={"remision":"Remisión","cedi_origen":"Origen","destino":"Destino","tortas":"Tortas","furgonetas":"Furg.","costo_flete":"Flete $","nocturno":"Noct.","created_at":"Fecha"}),use_container_width=True,hide_index=True)
    else: alerta("info","Sin despachos aún.")
    st.markdown('</div></div>', unsafe_allow_html=True)
    if st.button("↺  Actualizar"): st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── WMS: Inventario ──────────────────────────────────
elif mod=="WMS" and subpag=="Inventario":
    module_banner("Inventario CEDI","Control de stock · WMS · Responsable: Karen","tag-wms","WMS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    inv_df=get_inv(); stk=stock_total(inv_df); uso=stk/cfg("cap_almacen")*100
    cg,ci=st.columns([1,2])
    with cg: st.plotly_chart(gauge(stk,cfg("cap_almacen"),"USO DEL ALMACÉN"),use_container_width=True); alerta("info" if uso<65 else "warn" if uso<85 else "err",f"Al <b>{uso:.1f}%</b> — {cfg('cap_almacen')-stk:,} libres")
    with ci:
        c1,c2,c3=st.columns(3)
        for col,nom in [(c1,"Medellín"),(c2,"Santa Rosa"),(c3,"Taraza")]:
            sk=stock_cedi(inv_df,nom); est="🔴" if sk<=cfg("stock_min") else "🟡" if sk<=cfg("stock_min")*2 else "🟢"
            col.metric(f"{est} {nom}",f"{sk:,}",f"Mín:{cfg('stock_min')}"); col.progress(min(1.0,sk/(cfg("stock_min")*4)))
    st.divider()
    f1,f2=st.columns(2)
    with f1:
        st.markdown('<div class="dn-form"><div class="dn-form-title">REGISTRAR MOVIMIENTO</div>', unsafe_allow_html=True)
        cs=st.selectbox("CEDI",CEDIS); ts=st.selectbox("Tipo",["entrada","salida","ajuste"])
        qs=st.number_input("Cantidad",1,cfg("cap_almacen")); ds=st.text_input("Documento",placeholder="OC-2026-001")
        if st.button("Registrar Movimiento",use_container_width=True):
            sk2=stock_cedi(inv_df,cs)
            if ts=="salida" and sk2<qs: alerta("err",f"Stock insuficiente: {sk2}")
            elif ts=="entrada" and stk+qs>cfg("cap_almacen"): alerta("err",f"Supera capacidad. Solo caben {cfg('cap_almacen')-stk:,}.")
            else:
                nv=sk2+qs if ts=="entrada" else sk2-qs if ts=="salida" else qs
                db=supabase(); db.table("inventario").update({"stock":nv,"updated_at":datetime.now().isoformat()}).eq("cedi",cs).execute()
                db.table("movimientos").insert({"cedi":cs,"tipo":ts,"cantidad":qs,"documento":ds or "Sin doc","stock_result":nv,"usuario":usr_name}).execute()
                alerta("ok",f"{cs}: {sk2}→<b>{nv}</b>"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with f2:
        st.markdown('<div class="dn-section"><div class="dn-section-header">BITÁCORA</div><div class="dn-section-body">', unsafe_allow_html=True)
        mv=get_mov()
        if not mv.empty:
            ok=[c for c in ["created_at","cedi","tipo","cantidad","documento","stock_result"] if c in mv.columns]
            st.dataframe(mv[ok].rename(columns={"created_at":"Fecha","cedi":"CEDI","tipo":"Tipo","cantidad":"Cant.","documento":"Doc","stock_result":"Stock"}),use_container_width=True,hide_index=True,height=300)
        st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── WMS: Perecederos ─────────────────────────────────
elif mod=="WMS" and subpag=="Perecederos":
    module_banner("Control Perecederos",f"Sistema FIFO · Vida útil: {cfg('vida_util_dias')} días · Responsable: Karen","tag-wms","FIFO")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alerta("info",f"Sistema <b>FIFO</b> activo. Vida útil: <b>{cfg('vida_util_dias')} días</b>. Alerta: {cfg('alerta_vence_dias')} días antes.")
    t1,t2=st.tabs(["📋  LOTES ACTIVOS","➕  REGISTRAR LOTE"])
    with t1:
        lotes_df=get_lotes()
        if not lotes_df.empty and "fecha_vencimiento" in lotes_df.columns:
            hoy=date.today(); lotes_df["fv"]=pd.to_datetime(lotes_df["fecha_vencimiento"]).dt.date
            lotes_df["dias"]=lotes_df["fv"].apply(lambda x:(x-hoy).days)
            lotes_df["estado"]=lotes_df["dias"].apply(lambda d:"VENCIDO" if d<0 else "HOY" if d==0 else f"{d}d" if d<=cfg("alerta_vence_dias") else f"OK {d}d")
            for _,l in lotes_df[lotes_df["dias"]<0].iterrows(): alerta("err",f"<b>LOTE {l.get('lote_id','?')} ({l.get('cedi','?')}):</b> VENCIDO. Retirar.")
            for _,l in lotes_df[lotes_df["dias"]==0].iterrows(): alerta("err",f"<b>LOTE {l.get('lote_id','?')}:</b> vence HOY. Despachar urgente.")
            for _,l in lotes_df[(lotes_df["dias"]>0)&(lotes_df["dias"]<=cfg("alerta_vence_dias"))].iterrows(): alerta("warn",f"<b>LOTE {l.get('lote_id','?')}:</b> vence en {l['dias']}d. Priorizar.")
            ok_=[c for c in ["lote_id","cedi","cantidad","fecha_ingreso","fecha_vencimiento","dias","estado","proveedor"] if c in lotes_df.columns]
            st.dataframe(lotes_df[ok_].sort_values("dias"),use_container_width=True,hide_index=True)
        else: alerta("info","Sin lotes registrados.")
    with t2:
        c1,c2=st.columns(2)
        with c1:
            ced_l=st.selectbox("CEDI",CEDIS,key="lc"); qty_l=st.number_input("Tortas",1,cfg("cap_almacen"),100,key="lq")
            fi=st.date_input("Fecha ingreso",value=date.today(),key="lfi")
        with c2:
            fv=st.date_input("Fecha vencimiento",value=date.today()+timedelta(days=cfg("vida_util_dias")),key="lfv")
            prov=st.text_input("Proveedor",key="lp"); lid=st.text_input("ID Lote",placeholder=f"LOTE-{date.today().strftime('%Y%m%d')}",key="lid")
        vida=(fv-fi).days
        alerta("ok",f"Vida útil: {vida}d") if vida>0 else alerta("err","Fechas incorrectas")
        if st.button("Registrar Lote",use_container_width=True):
            if not lid: alerta("err","Ingresa ID.")
            else:
                try:
                    supabase().table("lotes").insert({"lote_id":lid,"cedi":ced_l,"cantidad":qty_l,"fecha_ingreso":fi.isoformat(),"fecha_vencimiento":fv.isoformat(),"proveedor":prov,"estado":"activo"}).execute()
                    alerta("ok",f"Lote <b>{lid}</b>: {qty_l} tortas en {ced_l}."); st.rerun()
                except Exception as e: alerta("err",f"Error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS: Rutas (planeador) ────────────────────────────
elif mod=="TMS" and subpag=="Rutas":
    rutas_df=get_rutas_db(); rutas_activas=rutas_df[rutas_df.get("activa",pd.Series([True]*len(rutas_df)))==True] if "activa" in rutas_df.columns else rutas_df
    module_banner("Planeador de Rutas","Control de tráfico · Entregas antes de las 5:00 A.M.","tag-tms","TMS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alerta("warn","⏰ Restricción: todas las entregas deben llegar <b>antes de las 5:00 A.M.</b> desde Medellín.")

    if rutas_activas.empty: alerta("err","No hay rutas configuradas. Ve a TMS → Gestión Rutas."); st.markdown('</div>',unsafe_allow_html=True); st.stop()

    veh_df=get_vehiculos(); veh_activos=veh_df[veh_df["estado"]=="Activo"] if not veh_df.empty else pd.DataFrame()

    cf,cr=st.columns([1,1])
    with cf:
        st.markdown('<div class="dn-form"><div class="dn-form-title">CONFIGURAR DESPACHO</div>', unsafe_allow_html=True)
        muns=rutas_activas["municipio"].tolist()
        mun=st.selectbox("Municipio de entrega",muns)
        row_r=rutas_activas[rutas_activas["municipio"]==mun].iloc[0]
        qty=st.number_input("Unidades a transportar",1,10000,168)

        # Seleccionar vehículo
        if not veh_activos.empty:
            veh_opts=veh_activos["codigo"].tolist()
            veh_sel=st.selectbox("Tipo de vehículo",veh_opts)
            row_v=veh_activos[veh_activos["codigo"]==veh_sel].iloc[0]
            cap_v=int(row_v["capacidad"]); tarifa_v=int(row_v["tarifa_km"])
        else:
            cap_v=168; tarifa_v=cfg("tarifa_km"); veh_sel="FRG-01"
            alerta("warn","Sin vehículos activos. Usando valores por defecto.")

        hora=st.time_input("Hora de salida")
        noc=st.checkbox(f"Jornada Nocturna (+{cfg('recargo_nocturno_pct')}%)",value=True)
        ida=st.checkbox("Incluir regreso vacío",value=True)
        reg=st.button("Registrar Despacho",use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    km=float(row_r["km"])*2 if ida else float(row_r["km"])
    furgs=math.ceil(qty/cap_v)
    flete=int(km*tarifa_v*furgs*(1+cfg("recargo_nocturno_pct")/100 if noc else 1))
    sal=str(row_r.get("salida_max","03:00")); sh,sm=sal.split(":")
    hora_ok=hora.hour<int(sh) or (hora.hour==int(sh) and hora.minute<=int(sm))

    with cr:
        st.markdown('<div class="dn-section"><div class="dn-section-header">TRAZABILIDAD</div><div class="dn-section-body">', unsafe_allow_html=True)
        alerta("ok","Horario factible ✓") if hora_ok else alerta("err",f"No llegas a tiempo. Máxima: {sal} AM.")
        inv_df=get_inv(); stk_mde=stock_cedi(inv_df,"Medellín")
        if stk_mde<qty: alerta("err",f"Stock insuficiente CEDI Medellín: {stk_mde}")
        st.dataframe(pd.DataFrame({"Campo":["Ruta","Distancia","Tiempo est.","Salida máx.","Vehículo","# Unidades","Jornada","Flete a cobrar","Ingreso/unidad"],
            "Valor":[f"Medellín→{mun}",f"{km:.1f}km",str(row_r.get("tiempo_est","—")),f"{sal} AM",f"{furgs}x {veh_sel}",f"{qty:,}","Nocturna" if noc else "Diurna",f"${flete:,}",f"${flete//qty:,}"]}),use_container_width=True,hide_index=True)
        kc1,kc2=st.columns(2); kc1.metric("Vehículos",furgs); kc2.metric("Flete Total",f"${flete:,}")
        st.markdown('</div></div>', unsafe_allow_html=True)

    if reg:
        inv_df=get_inv(); stk_mde=stock_cedi(inv_df,"Medellín")
        if stk_mde<qty: alerta("err","Stock insuficiente.")
        else:
            db=supabase(); num=f"REM-{1001+len(get_desp())}"
            db.table("inventario").update({"stock":stk_mde-qty,"updated_at":datetime.now().isoformat()}).eq("cedi","Medellín").execute()
            db.table("despachos").insert({"remision":num,"cedi_origen":"Medellín","destino":mun,"km":km,"tortas":qty,"furgonetas":furgs,"nocturno":noc,"costo_flete":flete,"usuario":usr_name}).execute()
            db.table("movimientos").insert({"cedi":"Medellín","tipo":"salida","cantidad":qty,"documento":num,"stock_result":stk_mde-qty,"usuario":usr_name}).execute()
            alerta("ok",f"<b>{num}</b> — {qty} uds → {mun} — Flete: <b>${flete:,}</b>"); st.balloons()

    st.divider()
    st.markdown('<div class="dn-section"><div class="dn-section-header">TABLA DE RUTAS ACTIVAS</div><div class="dn-section-body">', unsafe_allow_html=True)
    tabla_r=[]
    for _,r in rutas_activas.iterrows():
        c_d=int(float(r["km"])*cfg("tarifa_km")); c_n=int(c_d*(1+cfg("recargo_nocturno_pct")/100))
        tabla_r.append({"Municipio":r["municipio"],"KM":r["km"],"KM ida/vuelta":float(r["km"])*2,"Tiempo":r.get("tiempo_est","—"),"Flete diurno":f"${c_d:,}","Flete nocturno":f"${c_n:,}","Salida máx.":r.get("salida_max","—")})
    st.dataframe(pd.DataFrame(tabla_r),use_container_width=True,hide_index=True)
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS: Gestión Rutas ────────────────────────────────
elif mod=="TMS" and subpag=="Gestión Rutas":
    module_banner("Gestión de Rutas","Agregar · Editar · Activar o desactivar municipios de entrega","tag-tms","RUTAS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)

    t1,t2=st.tabs(["🗺️  RUTAS REGISTRADAS","➕  AGREGAR RUTA"])
    with t1:
        rutas_df=get_rutas_db()
        if not rutas_df.empty:
            st.markdown('<div class="dn-section"><div class="dn-section-header"><span>RUTAS CONFIGURADAS</span><span style="color:var(--txt3)">(edita directamente)</span></div><div class="dn-section-body">', unsafe_allow_html=True)
            cols_show=[c for c in ["municipio","km","tiempo_est","salida_max","lat","lon","activa"] if c in rutas_df.columns]
            st.dataframe(rutas_df[cols_show],use_container_width=True,hide_index=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            st.subheader("✏️ Editar ruta existente")
            mun_ed=st.selectbox("Municipio a editar",rutas_df["municipio"].tolist(),key="r_ed")
            row_ed=rutas_df[rutas_df["municipio"]==mun_ed].iloc[0]
            c1,c2,c3=st.columns(3)
            with c1:
                new_km   =st.number_input("KM desde Medellín",0.0,2000.0,float(row_ed["km"]),step=0.1,key="r_km")
                new_tpo  =st.text_input("Tiempo estimado",str(row_ed.get("tiempo_est","—")),key="r_tpo")
            with c2:
                new_sal  =st.text_input("Salida máxima (HH:MM)",str(row_ed.get("salida_max","03:00")),key="r_sal")
                new_lat  =st.number_input("Latitud",-90.0,90.0,float(row_ed.get("lat",7.0)),step=0.0001,format="%.4f",key="r_lat")
            with c3:
                new_lon  =st.number_input("Longitud",-180.0,180.0,float(row_ed.get("lon",-75.5)),step=0.0001,format="%.4f",key="r_lon")
                new_act  =st.checkbox("Ruta activa",bool(row_ed.get("activa",True)),key="r_act")
            ce1,ce2=st.columns(2)
            with ce1:
                if st.button("💾 Guardar cambios",use_container_width=True):
                    try:
                        supabase().table("rutas").update({"km":new_km,"tiempo_est":new_tpo,"salida_max":new_sal,"lat":new_lat,"lon":new_lon,"activa":new_act}).eq("municipio",mun_ed).execute()
                        alerta("ok",f"Ruta <b>{mun_ed}</b> actualizada."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
            with ce2:
                if st.button("🗑️ Eliminar ruta",use_container_width=True):
                    try:
                        supabase().table("rutas").delete().eq("municipio",mun_ed).execute()
                        alerta("ok",f"Ruta {mun_ed} eliminada."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
        else:
            alerta("info","Sin rutas. Agrega la primera.")

    with t2:
        st.markdown('<div class="dn-form"><div class="dn-form-title">NUEVA RUTA DE DISTRIBUCIÓN</div>', unsafe_allow_html=True)
        alerta("info","Las coordenadas GPS (lat/lon) son necesarias para el mapa interactivo. Puedes obtenerlas en Google Maps haciendo clic derecho sobre el municipio.")
        c1,c2=st.columns(2)
        with c1:
            n_mun=st.text_input("Nombre del municipio",placeholder="Ej: Briceño")
            n_km =st.number_input("Distancia desde Medellín (km)",0.0,2000.0,100.0,step=0.1)
            n_tpo=st.text_input("Tiempo estimado de viaje",placeholder="Ej: 2h 30m")
        with c2:
            n_sal=st.text_input("Hora de salida máxima (HH:MM)",placeholder="03:00",help="Máximo para llegar antes de las 5:00 AM")
            n_lat=st.number_input("Latitud GPS",-90.0,90.0,7.0,step=0.0001,format="%.4f")
            n_lon=st.number_input("Longitud GPS",-180.0,0.0,-75.5,step=0.0001,format="%.4f")

        # Vista previa automática de costos
        if n_km > 0 and n_sal:
            c_d=int(n_km*cfg("tarifa_km")); c_n=int(c_d*(1+cfg("recargo_nocturno_pct")/100))
            alerta("info",f"Vista previa: Flete diurno <b>${c_d:,}</b> · Flete nocturno <b>${c_n:,}</b> (1 furgoneta, ida/vuelta: ${c_d*2:,} / ${c_n*2:,})")

        if st.button("➕ Agregar Ruta",use_container_width=True):
            if not n_mun or n_km<=0: alerta("err","Ingresa nombre y km.")
            elif not n_sal or ":" not in n_sal: alerta("err","Formato de hora: HH:MM (ej: 03:00)")
            else:
                try:
                    supabase().table("rutas").insert({"municipio":n_mun.strip(),"km":n_km,"tiempo_est":n_tpo,"salida_max":n_sal,"lat":n_lat,"lon":n_lon,"activa":True}).execute()
                    alerta("ok",f"Ruta <b>{n_mun}</b> agregada exitosamente."); st.rerun()
                except Exception as e: alerta("err",f"Error (¿municipio duplicado?): {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS: Mapa ────────────────────────────────────────
elif mod=="TMS" and subpag=="Mapa":
    module_banner("Mapa de CEDIs y Rutas","Trayectos norte de Antioquia · Rutas dinámicas","tag-tms","GEO")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    if not FOLIUM_OK: alerta("warn","Instala <code>pip install folium streamlit-folium</code>")
    rutas_df=get_rutas_db()
    cm_,ci_=st.columns([3,1])
    with cm_:
        if FOLIUM_OK and not rutas_df.empty:
            m_map=folium.Map(location=[6.9,-75.5],zoom_start=8,tiles="CartoDB dark_matter")
            folium.Marker([6.2442,-75.5812],popup="<b>DistriNova CEDI Medellín</b>",tooltip="🏙️ CEDI Medellín",icon=folium.Icon(color="blue",icon="home",prefix="fa")).add_to(m_map)
            palette=["green","orange","cadetblue","beige","red","purple","darkred","lightblue"]
            activas=rutas_df[rutas_df.get("activa",pd.Series([True]*len(rutas_df)))==True] if "activa" in rutas_df.columns else rutas_df
            for i,(_,r) in enumerate(activas.iterrows()):
                if pd.notna(r.get("lat")) and pd.notna(r.get("lon")):
                    folium.Marker([r["lat"],r["lon"]],popup=f"<b>{r['municipio']}</b><br>{r['km']} km",tooltip=f"🏘️ {r['municipio']}",icon=folium.Icon(color=palette[i%len(palette)],icon="truck",prefix="fa")).add_to(m_map)
                    folium.PolyLine([[6.2442,-75.5812],[r["lat"],r["lon"]]],color="#FF8C00",weight=2.5,opacity=0.7,dash_array="8 4",tooltip=f"→ {r['municipio']}: {r['km']} km").add_to(m_map)
            st_folium(m_map,width=None,height=500)
        else:
            st.markdown("<div style='background:var(--bg3);border-radius:10px;padding:60px;text-align:center;color:var(--txt3)'><div style='font-size:48px'>🗺️</div><div style='margin-top:12px'>Instala folium o agrega rutas primero</div></div>",unsafe_allow_html=True)
    with ci_:
        st.markdown('<div class="dn-section"><div class="dn-section-header">CEDIs ACTIVOS</div><div class="dn-section-body">', unsafe_allow_html=True)
        inv_df=get_inv()
        for ic2,nm,rl in [("🏙️","Medellín","Principal"),("🏘️","Santa Rosa","Distribución"),("🏜️","Taraza","Distribución")]:
            sk=stock_cedi(inv_df,nm)
            st.markdown(f'<div class="dn-cedi" style="margin-bottom:10px"><div class="dn-cedi-tag">{rl}</div><div class="dn-cedi-name">{ic2} {nm}</div><div class="dn-cedi-stock">{sk:,}</div><div style="font-size:10px;color:var(--txt3)">unidades</div></div>',unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
        if not rutas_df.empty:
            st.markdown('<div class="dn-section" style="margin-top:12px"><div class="dn-section-header">RUTAS ACTIVAS</div><div class="dn-section-body">', unsafe_allow_html=True)
            activas=rutas_df[rutas_df.get("activa",pd.Series([True]*len(rutas_df)))==True] if "activa" in rutas_df.columns else rutas_df
            for _,r in activas.iterrows():
                st.markdown(f"<div style='padding:6px 0;border-bottom:1px solid var(--border);font-size:12px'><b style='color:var(--txt)'>{r['municipio']}</b><br><span style='color:var(--txt2)'>{r['km']} km · {r.get('tiempo_est','—')}</span></div>",unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TMS: Pedidos ─────────────────────────────────────
elif mod=="TMS" and subpag=="Pedidos":
    module_banner("Órdenes de Servicio","Gestión de pedidos de transporte y distribución","tag-tms","ODS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    rutas_df=get_rutas_db()
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="dn-form"><div class="dn-form-title">NUEVA ORDEN</div>', unsafe_allow_html=True)
        act=st.selectbox("Solicitante",["Fabricante→DistriNova","Mayorista→DistriNova","Minorista→DistriNova","Min.Defensa→DistriNova"])
        dst=st.selectbox("Destino",rutas_df["municipio"].tolist() if not rutas_df.empty else ["Medellín"])
        qp=st.number_input("Unidades",1,10000,168); pvp=st.number_input("Tarifa acordada ($)",0,500000,0)
        obs=st.text_area("Observaciones",height=70)
        if st.button("Crear Orden",use_container_width=True):
            supabase().table("pedidos").insert({"actor":act,"destino":dst,"cantidad":qp,"precio_unit":pvp,"total":pvp,"observaciones":obs,"usuario":usr_name}).execute()
            alerta("ok",f"Orden: {qp} uds→{dst}"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        pf=get_ped(); k1,k2,k3=st.columns(3)
        k1.metric("Órdenes",len(pf))
        if not pf.empty: k2.metric("Unidades",f"{pf['cantidad'].sum():,}"); k3.metric("Ingresos",f"${pf['total'].sum():,}")
        st.dataframe(pf if not pf.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── FIN: Cotizador ───────────────────────────────────
elif mod=="FIN" and subpag=="Cotizador":
    module_banner("Cotizador Logístico","DistriNova factura por transporte · almacenamiento · alistamiento · manipulación","tag-fin","FIN")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    rutas_df=get_rutas_db(); veh_df=get_vehiculos()
    alerta("info","DistriNova es <b>operador logístico</b>. No vende tortas. Factura por sus servicios al fabricante o mayorista.")
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="dn-form"><div class="dn-form-title">PARÁMETROS</div>', unsafe_allow_html=True)
        rc=st.selectbox("Ruta",rutas_df["municipio"].tolist() if not rutas_df.empty else [])
        qty_c=st.number_input("Unidades",1,10000,168)
        dias_alm=st.number_input("Días almacenamiento previo",0,30,1)
        noc_c=st.checkbox(f"Nocturna (+{cfg('recargo_nocturno_pct')}%)",value=True)
        ida_c=st.checkbox("Regreso vacío",value=True); cliente=st.text_input("Cliente")
        veh_activos=veh_df[veh_df["estado"]=="Activo"] if not veh_df.empty else pd.DataFrame()
        if not veh_activos.empty:
            v_sel=st.selectbox("Tipo de vehículo",veh_activos["codigo"].tolist())
            cap_v=int(veh_activos[veh_activos["codigo"]==v_sel].iloc[0]["capacidad"])
            tar_v=int(veh_activos[veh_activos["codigo"]==v_sel].iloc[0]["tarifa_km"])
        else: cap_v=168; tar_v=cfg("tarifa_km")
        st.markdown('</div>', unsafe_allow_html=True)
    if rc and not rutas_df.empty:
        rd=rutas_df[rutas_df["municipio"]==rc].iloc[0]
        km_c=float(rd["km"])*2 if ida_c else float(rd["km"])
        furgs_c=math.ceil(qty_c/cap_v)
        c_fl=int(km_c*tar_v*furgs_c*(1+cfg("recargo_nocturno_pct")/100 if noc_c else 1))
        c_alm=qty_c*cfg("tarifa_almacenamiento")*dias_alm
        c_alis=qty_c*cfg("tarifa_alistamiento")
        c_mani=qty_c*cfg("tarifa_manipulacion")
        c_adm=int(c_fl*cfg("tarifa_admin_pct")/100)
        c_tot=c_fl+c_alm+c_alis+c_mani+c_adm; c_ppu=c_tot//qty_c if qty_c else 0
        with c2:
            st.markdown('<div class="dn-section"><div class="dn-section-header">DESGLOSE DE COBROS</div><div class="dn-section-body">', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame({"Servicio":["🚐 Transporte","🏭 Almacenamiento","📦 Alistamiento","🔄 Manipulación",f"📋 Admin({cfg('tarifa_admin_pct')}%)"],
                "Base":[f"{km_c}km×${tar_v:,}×{furgs_c}",f"{qty_c}×${cfg('tarifa_almacenamiento'):,}×{dias_alm}d",f"{qty_c}×${cfg('tarifa_alistamiento'):,}",f"{qty_c}×${cfg('tarifa_manipulacion'):,}",f"{cfg('tarifa_admin_pct')}% del flete"],
                "Cobro":[f"${c_fl:,}",f"${c_alm:,}",f"${c_alis:,}",f"${c_mani:,}",f"${c_adm:,}"]}),use_container_width=True,hide_index=True)
            k1,k2=st.columns(2); k1.metric("TOTAL FACTURAR",f"${c_tot:,}"); k2.metric("Ingreso/unidad",f"${c_ppu:,}")
            alerta("ok",f"DistriNova factura <b>${c_tot:,}</b> a {cliente if cliente else 'el cliente'}.")
            st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── FIN: Documentos ──────────────────────────────────
elif mod=="FIN" and subpag=="Documentos":
    module_banner("Remisiones y Facturas","Documentos de servicio logístico · Responsable: Mafe","tag-fin","DOCS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    t1,t2=st.tabs(["📄  REMISIONES","🧾  FACTURAS"])
    with t1:
        df=get_desp()
        if not df.empty and "remision" in df.columns:
            sel=st.selectbox("Despacho",df["remision"].tolist()); row=df[df["remision"]==sel].iloc[0]
            st.markdown(f"### 📄 {sel}\n| Campo|Valor|\n|---|---|\n|Empresa|DistriNova|\n|Número|{sel}|\n|Fecha|{str(row.get('created_at',''))[:10]}|\n|Origen|{row['cedi_origen']}|\n|Destino|{row['destino']}|\n|KM|{row['km']}|\n|Unidades|**{row['tortas']}**|\n|Furgonetas|{row['furgonetas']}|\n|Jornada|{'Nocturna' if row['nocturno'] else 'Diurna'}|\n|Flete|**${int(row['costo_flete']):,}**|\n|Responsable|{row.get('usuario','—')}|")
        else: alerta("info","Sin despachos.")
    with t2:
        c1,c2=st.columns(2)
        with c1:
            st.markdown('<div class="dn-form">', unsafe_allow_html=True)
            clf=st.text_input("Cliente"); nit=st.text_input("NIT")
            qf=st.number_input("Unidades",0,10000,168)
            f_fl=st.number_input("Cobro transporte($)",0); f_al=st.number_input("Almacenamiento($)",0)
            f_as=st.number_input("Alistamiento($)",0); f_ma=st.number_input("Manipulación($)",0)
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            sub=f_fl+f_al+f_as+f_ma; iva=int(sub*.19); tot=sub+iva
            k1,k2,k3=st.columns(3); k1.metric("Subtotal",f"${sub:,}"); k2.metric("IVA 19%",f"${iva:,}"); k3.metric("TOTAL",f"${tot:,}")
            if st.button("Guardar Factura",use_container_width=True):
                if not clf: alerta("err","Ingresa cliente.")
                else:
                    cnt=supabase().table("facturas").select("id",count="exact").execute()
                    nf=f"FAC-{2001+(cnt.count or 0)}"
                    supabase().table("facturas").insert({"numero":nf,"cliente":clf,"nit":nit,"cantidad":qf,"precio_unit":sub//qf if qf else 0,"costo_flete":f_fl,"subtotal":sub,"iva":iva,"total":tot,"ruta":"Servicios logísticos","usuario":"Mafe"}).execute()
                    alerta("ok",f"Factura <b>{nf}</b> — Total:<b>${tot:,}</b>")
    st.markdown('</div>', unsafe_allow_html=True)

# ── FIN: Historial ───────────────────────────────────
elif mod=="FIN" and subpag=="Historial":
    module_banner("Historial de Transacciones","Registro completo de operaciones","tag-fin","LOG")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    df=get_desp(); pf=get_ped(); mf=get_mov()
    k1,k2,k3,k4=st.columns(4)
    k1.metric("Despachos",len(df)); k2.metric("Órdenes",len(pf))
    k3.metric("Tortas",f"{df['tortas'].sum():,}" if not df.empty else 0)
    k4.metric("Ingresos",f"${df['costo_flete'].sum():,}" if not df.empty else "$0")
    if not df.empty and "destino" in df.columns:
        cc1,cc2=st.columns(2)
        with cc1:
            grp=df.groupby("destino")["costo_flete"].sum().reset_index()
            fig=px.pie(grp,values="costo_flete",names="destino",title="Ingresos por ruta",color_discrete_sequence=["#1E88E5","#FF8C00","#00C97A","#FFB800","#5A7A99"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#5A7A99"),title_font=dict(color="#C8D8EA",size=12),height=250,margin=dict(t=36,b=0,l=0,r=0))
            st.plotly_chart(fig,use_container_width=True)
        with cc2:
            grp2=df.groupby("destino")["tortas"].sum().reset_index()
            st.plotly_chart(mini_chart(grp2["destino"].tolist(),grp2["tortas"].tolist(),"#FF8C00",height=250),use_container_width=True)
    t1,t2,t3=st.tabs(["🚐  DESPACHOS","🛒  ÓRDENES","📦  INVENTARIO"])
    with t1: st.dataframe(df if not df.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    with t2: st.dataframe(pf if not pf.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    with t3: st.dataframe(mf if not mf.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── SYS: Flota ───────────────────────────────────────
elif mod=="SYS" and subpag=="Flota":
    module_banner("Gestión de Flota","Agregar · Editar · Calcular capacidad por cubicaje","tag-sys","FLOTA")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    alerta("info","La <b>capacidad</b> se calcula automáticamente por cubicaje: (ancho÷caja_ancho) × (largo÷caja_largo) × min(alto÷caja_alto, arrume_máx)")

    veh_df=get_vehiculos()

    # Cards de vehículos
    if not veh_df.empty:
        n_cols=min(4,len(veh_df)); cols=st.columns(n_cols)
        for i,(_,v) in enumerate(veh_df.iterrows()):
            with cols[i%n_cols]:
                est_c="status-ok" if v.get("estado")=="Activo" else "status-warn" if v.get("estado")=="Reserva" else "status-err"
                st.markdown(f"""
                <div class="veh-card">
                    <div class="veh-status"><span class="dn-status {est_c}">{v.get('estado','—')}</span></div>
                    <div class="veh-codigo">{v.get('codigo','')}</div>
                    <div class="veh-tipo">{v.get('tipo','Vehículo')}</div>
                    <div class="veh-cap">{int(v.get('capacidad',0)):,}</div>
                    <div style="font-size:10px;color:var(--txt3)">tortas por viaje</div>
                    <div class="veh-dim">📐 {v.get('ancho_m','?')}×{v.get('largo_m','?')}×{v.get('alto_m','?')} m</div>
                    <div class="veh-dim">💵 ${int(v.get('tarifa_km',3000)):,}/km · Arrume máx: {v.get('arrume_max',3)}</div>
                </div>""", unsafe_allow_html=True)

    st.divider()
    t1,t2=st.tabs(["✏️  EDITAR VEHÍCULO","➕  AGREGAR VEHÍCULO"])

    with t1:
        if not veh_df.empty:
            v_ed=st.selectbox("Vehículo",veh_df["codigo"].tolist())
            row_v=veh_df[veh_df["codigo"]==v_ed].iloc[0]
            c1,c2,c3=st.columns(3)
            with c1:
                n_tipo=st.text_input("Tipo",str(row_v.get("tipo","Furgoneta")))
                n_aw=st.number_input("Ancho del vehículo (m)",0.1,10.0,float(row_v.get("ancho_m",2.2)),step=0.01)
                n_al=st.number_input("Largo del vehículo (m)",0.1,20.0,float(row_v.get("largo_m",2.5)),step=0.01)
                n_ah=st.number_input("Alto del vehículo (m)",0.1,10.0,float(row_v.get("alto_m",1.8)),step=0.01)
            with c2:
                n_ca=st.number_input("Ancho caja torta (m)",0.01,2.0,float(row_v.get("caja_ancho",0.30)),step=0.01)
                n_cl=st.number_input("Largo caja torta (m)",0.01,2.0,float(row_v.get("caja_largo",0.30)),step=0.01)
                n_ch=st.number_input("Alto caja torta (m)",0.01,2.0,float(row_v.get("caja_alto",0.15)),step=0.01)
                n_arr=st.number_input("Arrume máximo (pilas)",1,10,int(row_v.get("arrume_max",3)))
            with c3:
                n_tar=st.number_input("Tarifa/km ($)",0,100000,int(row_v.get("tarifa_km",3000)),step=100)
                n_est=st.selectbox("Estado",["Activo","Reserva","En taller","Fuera de servicio"],index=["Activo","Reserva","En taller","Fuera de servicio"].index(row_v.get("estado","Activo")) if row_v.get("estado","Activo") in ["Activo","Reserva","En taller","Fuera de servicio"] else 0)
                n_notas=st.text_area("Notas",str(row_v.get("notas","") or ""),height=80)
                nueva_cap=calcular_capacidad(n_aw,n_al,n_ah,n_ca,n_cl,n_ch,n_arr)
                st.metric("📦 Capacidad calculada",f"{nueva_cap:,} tortas")
            ce1,ce2=st.columns(2)
            with ce1:
                if st.button("💾 Guardar cambios",use_container_width=True):
                    try:
                        supabase().table("vehiculos").update({"tipo":n_tipo,"ancho_m":n_aw,"largo_m":n_al,"alto_m":n_ah,"caja_ancho":n_ca,"caja_largo":n_cl,"caja_alto":n_ch,"arrume_max":n_arr,"capacidad":nueva_cap,"tarifa_km":n_tar,"estado":n_est,"notas":n_notas}).eq("codigo",v_ed).execute()
                        alerta("ok",f"Vehículo <b>{v_ed}</b> actualizado. Capacidad: <b>{nueva_cap}</b> tortas."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")
            with ce2:
                if st.button("🗑️ Eliminar vehículo",use_container_width=True):
                    try:
                        supabase().table("vehiculos").delete().eq("codigo",v_ed).execute()
                        alerta("ok",f"Vehículo {v_ed} eliminado."); st.rerun()
                    except Exception as e: alerta("err",f"Error: {e}")

    with t2:
        st.markdown('<div class="dn-form"><div class="dn-form-title">NUEVO VEHÍCULO</div>', unsafe_allow_html=True)
        alerta("info","Ingresa las dimensiones del vehículo y de la caja de torta. La capacidad se calcula automáticamente.")
        c1,c2,c3=st.columns(3)
        with c1:
            nv_cod=st.text_input("Código único",placeholder="FRG-05")
            nv_tipo=st.text_input("Tipo de vehículo",placeholder="Camión 3/4, Furgoneta, etc.")
            nv_aw=st.number_input("Ancho interior (m)",0.1,10.0,2.2,step=0.01,key="nv_aw")
            nv_al=st.number_input("Largo interior (m)",0.1,20.0,2.5,step=0.01,key="nv_al")
            nv_ah=st.number_input("Alto interior (m)",0.1,10.0,1.8,step=0.01,key="nv_ah")
        with c2:
            nv_ca=st.number_input("Ancho caja torta (m)",0.01,2.0,0.30,step=0.01,key="nv_ca")
            nv_cl=st.number_input("Largo caja torta (m)",0.01,2.0,0.30,step=0.01,key="nv_cl")
            nv_ch=st.number_input("Alto caja torta (m)",0.01,2.0,0.15,step=0.01,key="nv_ch")
            nv_arr=st.number_input("Arrume máximo",1,10,3,key="nv_arr")
        with c3:
            nv_tar=st.number_input("Tarifa/km ($)",0,100000,3000,step=100,key="nv_tar")
            nv_est=st.selectbox("Estado inicial",["Activo","Reserva"],key="nv_est")
            nv_notas=st.text_area("Notas opcionales",height=80,key="nv_notas")
            nv_cap=calcular_capacidad(nv_aw,nv_al,nv_ah,nv_ca,nv_cl,nv_ch,nv_arr)
            st.metric("📦 Capacidad calculada",f"{nv_cap:,} tortas")

        if st.button("➕ Agregar Vehículo",use_container_width=True):
            if not nv_cod or not nv_tipo: alerta("err","Ingresa código y tipo.")
            elif nv_cap<=0: alerta("err","Capacidad 0 — revisa dimensiones.")
            else:
                try:
                    supabase().table("vehiculos").insert({"codigo":nv_cod.strip(),"tipo":nv_tipo,"ancho_m":nv_aw,"largo_m":nv_al,"alto_m":nv_ah,"caja_ancho":nv_ca,"caja_largo":nv_cl,"caja_alto":nv_ch,"arrume_max":nv_arr,"capacidad":nv_cap,"tarifa_km":nv_tar,"estado":nv_est,"notas":nv_notas}).execute()
                    alerta("ok",f"Vehículo <b>{nv_cod}</b> agregado. Capacidad: <b>{nv_cap}</b> tortas."); st.rerun()
                except Exception as e: alerta("err",f"Error (¿código duplicado?): {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── SYS: Configuración ───────────────────────────────
elif mod=="SYS" and subpag=="Configuración":
    module_banner("Configuración del Sistema","Todos los valores editables en tiempo real","tag-sys","SYS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    t1,t2,t3=st.tabs(["💵  TARIFAS","📦  ALMACÉN","🍰  PERECEDEROS"])
    with t1:
        c1,c2=st.columns(2)
        with c1:
            st.session_state["cfg_tarifa_km"]=st.number_input("Tarifa base/km ($)",0,50000,int(cfg("tarifa_km")),step=100)
            st.session_state["cfg_recargo_nocturno_pct"]=st.number_input("Recargo nocturno (%)",0,100,int(cfg("recargo_nocturno_pct")))
            st.session_state["cfg_tarifa_almacenamiento"]=st.number_input("Almacenamiento ($/ud/día)",0,10000,int(cfg("tarifa_almacenamiento")),step=10)
        with c2:
            st.session_state["cfg_tarifa_alistamiento"]=st.number_input("Alistamiento ($/ud)",0,5000,int(cfg("tarifa_alistamiento")),step=10)
            st.session_state["cfg_tarifa_manipulacion"]=st.number_input("Manipulación ($/ud)",0,5000,int(cfg("tarifa_manipulacion")),step=10)
            st.session_state["cfg_tarifa_admin_pct"]=st.number_input("Administración (% flete)",0,50,int(cfg("tarifa_admin_pct")))
    with t2:
        c1,c2=st.columns(2)
        with c1: st.session_state["cfg_cap_almacen"]=st.number_input("Capacidad máx. (uds)",100,50000,int(cfg("cap_almacen")),step=100)
        with c2: st.session_state["cfg_stock_min"]=st.number_input("Stock mínimo por CEDI",0,500,int(cfg("stock_min")))
    with t3:
        c1,c2=st.columns(2)
        with c1: st.session_state["cfg_vida_util_dias"]=st.number_input("Vida útil tortas (días)",1,30,int(cfg("vida_util_dias")))
        with c2: st.session_state["cfg_alerta_vence_dias"]=st.number_input("Alertar (días antes de vencimiento)",1,10,int(cfg("alerta_vence_dias")))
    alerta("ok","Los cambios aplican en toda la sesión.")
    st.markdown('</div>', unsafe_allow_html=True)

# ── SYS: Especificaciones ────────────────────────────
elif mod=="SYS" and subpag=="Especificaciones":
    module_banner("Especificaciones Operativas","Parámetros técnicos · Estructura operacional","tag-sys","OPS")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    veh_df=get_vehiculos(); rutas_df=get_rutas_db(); inv_df=get_inv()
    veh_act=len(veh_df[veh_df["estado"]=="Activo"]) if not veh_df.empty else 0
    cap_flota=int(veh_df[veh_df["estado"]=="Activo"]["capacidad"].sum()) if not veh_df.empty else 0
    k1,k2,k3,k4=st.columns(4)
    k1.metric("Vehículos activos",veh_act); k2.metric("Cap. flota/viaje",f"{cap_flota:,}")
    k3.metric("Rutas activas",len(rutas_df)); k4.metric("Cap. almacén",f"{cfg('cap_almacen'):,}")
    t1,t2,t3=st.tabs(["🚐  FLOTA","🗺️  RUTAS","💰  TARIFAS"])
    with t1: st.dataframe(veh_df if not veh_df.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    with t2: st.dataframe(rutas_df if not rutas_df.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    with t3:
        st.markdown(f"|Servicio|Tarifa|\n|---|---|\n|Transporte|${cfg('tarifa_km'):,}/km|\n|Nocturno|+{cfg('recargo_nocturno_pct')}%|\n|Almacenamiento|${cfg('tarifa_almacenamiento'):,}/ud/día|\n|Alistamiento|${cfg('tarifa_alistamiento'):,}/ud|\n|Manipulación|${cfg('tarifa_manipulacion'):,}/ud|\n|Admin|{cfg('tarifa_admin_pct')}% del flete|")
    st.markdown('</div>', unsafe_allow_html=True)

# ── SYS: Equipo ──────────────────────────────────────
elif mod=="SYS" and subpag=="Equipo":
    module_banner("Equipo Operativo","Roles y responsabilidades DistriNova","tag-sys","RH")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)
    eq=[("👑","Yoany","COO · Director Operaciones","#1E88E5","KPIs · Junta · Estrategia","WMS·TMS·FIN·SYS·IA"),
        ("🗺️","Gómez","Coord. Logística y Tráfico","#FF8C00","Rutas · GPS · Nocturnos","TMS"),
        ("📦","Karen","Analista Inventarios","#00C97A","Stock · Perecederos FIFO","WMS"),
        ("🚛","Laura","Auxiliar Operaciones","#FFB800","Cargue · Estiba · Verificación","WMS·TMS"),
        ("🧾","Mafe","Facturación y Documentación","#42A5F5","Facturas · Remisiones","FIN")]
    cols=st.columns(3)
    for i,(em,nom,cargo,color,resp,mods) in enumerate(eq):
        with cols[i%3]:
            st.markdown(f'<div class="dn-section" style="margin-bottom:10px"><div style="display:flex;align-items:center;gap:14px;padding:14px 18px"><div style="font-size:28px;width:42px;text-align:center">{em}</div><div style="flex:1"><div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:{color};margin-bottom:2px">{cargo}</div><div style="font-family:var(--cond);font-size:18px;font-weight:700;color:white">{nom}</div><div style="font-size:11px;color:var(--txt2);margin-top:2px">{resp}</div></div><div style="text-align:right;font-size:10px;color:{color};font-weight:600">{mods}</div></div></div>',unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# IA: ASISTENTE
# ════════════════════════════════
elif mod=="IA" and subpag=="Asistente":
    module_banner("NOVA — Asistente IA","Inteligencia artificial con acceso al estado real de la operación","tag-ia","IA")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)

    alerta("ia","◈ <b>NOVA</b> tiene acceso en tiempo real a: stock, rutas, flota, costos, perecederos y despachos. Puedes preguntar cualquier cosa sobre la operación.")

    # Sugerencias rápidas
    st.markdown('<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">', unsafe_allow_html=True)
    sugs=[
        "¿Cuál es el estado actual del inventario?",
        "¿Cuántas furgonetas necesito hoy para 520 tortas?",
        "¿Qué ruta tiene el flete más costoso?",
        "¿Hay lotes próximos a vencer?",
        "Genera un resumen de KPIs para la junta directiva",
        "¿Qué ruta conviene más para 200 tortas esta noche?",
    ]
    c_sugs=st.columns(3)
    for i,sg in enumerate(sugs):
        with c_sugs[i%3]:
            if st.button(sg, key=f"sug_{i}", use_container_width=True):
                save_msg("user", sg)
                with st.spinner("◈ NOVA está analizando..."):
                    resp=call_claude(st.session_state.ia_msgs[:-1], sg)
                save_msg("assistant", resp)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Historial del chat
    if st.session_state.ia_msgs:
        st.markdown('<div class="dn-section"><div class="dn-section-header"><span>CONVERSACIÓN</span><span style="color:var(--txt3)">{} mensajes</span></div><div class="dn-section-body" style="max-height:420px;overflow-y:auto">'.format(len(st.session_state.ia_msgs)), unsafe_allow_html=True)
        for msg in st.session_state.ia_msgs:
            render_msg(msg)
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;padding:40px;color:var(--txt3)"><div style="font-size:40px;margin-bottom:12px">◈</div><div style="font-family:var(--cond);font-size:18px">NOVA lista</div><div style="font-size:12px;margin-top:6px">Usa las sugerencias o escribe tu pregunta abajo</div></div>',unsafe_allow_html=True)

    # Input del usuario
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        user_input = st.text_input("", placeholder="Escribe tu pregunta sobre la operación...", label_visibility="collapsed", key="ia_input")
    with col_btn:
        send = st.button("Enviar ▶", use_container_width=True)

    if send and user_input.strip():
        save_msg("user", user_input)
        with st.spinner("◈ NOVA analizando datos..."):
            resp = call_claude(st.session_state.ia_msgs[:-1], user_input)
        save_msg("assistant", resp)
        st.rerun()

    col_c1, col_c2 = st.columns([1, 5])
    with col_c1:
        if st.button("🗑️ Limpiar chat"):
            st.session_state.ia_msgs = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# IA: ANÁLISIS / REPORTE KPI
# ════════════════════════════════
elif mod=="IA" and subpag=="Análisis":
    module_banner("Análisis Automático de KPIs","NOVA genera reportes inteligentes basados en datos reales","tag-ia","KPI")
    st.markdown('<div class="dn-content">', unsafe_allow_html=True)

    reportes = {
        "📊 Reporte ejecutivo para Junta Directiva": "Genera un reporte ejecutivo completo para presentar a la Junta Directiva de DistriNova. Incluye: estado del inventario, desempeño de flota, ingresos por fletes, alertas críticas y 3 recomendaciones estratégicas. Usa un tono formal y estructurado.",
        "🚐 Optimización de flota para hoy": "Analiza la flota disponible y el stock actual. ¿Cuántos vehículos necesito para despachar entre 500 y 600 tortas hoy? ¿Cuál es la combinación óptima de rutas? ¿Hay algún problema operativo que deba resolver primero?",
        "💵 Análisis financiero de rutas": "Analiza todas las rutas activas. ¿Cuál genera más ingreso por km recorrido? ¿Cuál tiene mejor relación costo-beneficio? ¿Hay alguna ruta que no sea rentable con la tarifa actual? Dame una tabla comparativa.",
        "🍰 Alerta de perecederos": "Revisa todos los lotes de perecederos. Identifica riesgos de vencimiento, pérdidas potenciales y recomienda qué despachar prioritariamente hoy. Si no hay lotes críticos, sugiere cómo mejorar la rotación.",
        "🏭 Estado de CEDIs y recomendaciones": "Analiza el stock de cada CEDI. ¿Alguno está en riesgo de ruptura o de superar capacidad? ¿Qué transferencias inter-CEDI recomendarías? ¿Cuándo se debe emitir la próxima orden de compra?",
    }

    st.markdown('<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">', unsafe_allow_html=True)
    for nombre, prompt in reportes.items():
        if st.button(nombre, key=f"rep_{nombre}", use_container_width=True):
            st.session_state["reporte_activo"] = nombre
            st.session_state["reporte_prompt"] = prompt
            with st.spinner(f"◈ NOVA generando: {nombre}..."):
                resp = call_claude([], prompt)
            st.session_state["reporte_resultado"] = resp
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if "reporte_resultado" in st.session_state:
        import re
        txt = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', st.session_state["reporte_resultado"])
        st.markdown(f"""
        <div class="dn-section">
            <div class="dn-section-header">
                <span>◈ {st.session_state.get('reporte_activo','REPORTE')}</span>
                <span style="color:var(--txt3)">Generado por NOVA</span>
            </div>
            <div class="dn-section-body" style="line-height:1.7;font-size:13px;color:var(--txt)">
                {txt.replace(chr(10),'<br>')}
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("🗑️ Limpiar reporte"):
            del st.session_state["reporte_resultado"]
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
