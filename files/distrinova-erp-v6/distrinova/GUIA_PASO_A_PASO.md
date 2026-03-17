# 🚀 DistriNova ERP — Guía de Instalación Paso a Paso
# Para principiantes en Python · VS Code

---

## PASO 1 — Instalar lo necesario en tu computador

### 1.1 Instalar Python
1. Ve a: https://www.python.org/downloads/
2. Descarga **Python 3.11** (el botón amarillo grande)
3. Al instalar, **marca la casilla** "Add Python to PATH" ✅
4. Haz clic en "Install Now"

### 1.2 Instalar VS Code
1. Ve a: https://code.visualstudio.com/
2. Descarga e instala normalmente

### 1.3 Extensiones de VS Code (instálalas dentro del programa)
Abre VS Code y presiona **Ctrl+Shift+X**, busca e instala:
- ✅ **Python** (de Microsoft)
- ✅ **Pylance** (de Microsoft)
- ✅ **GitLens** (para GitHub)

---

## PASO 2 — Crear la cuenta en Supabase (base de datos gratis)

1. Ve a: https://supabase.com
2. Clic en **"Start your project"**
3. Regístrate con tu cuenta de Google o GitHub
4. Clic en **"New Project"**
5. Ponle nombre: `distrinova-erp`
6. Crea una contraseña segura (guárdala)
7. Elige región: **South America (São Paulo)**
8. Espera ~2 minutos mientras crea el proyecto

### 2.1 Crear las tablas en Supabase
Una vez creado el proyecto:
1. Ve a la sección **"SQL Editor"** (menú izquierdo)
2. Copia y pega el contenido del archivo `supabase_tablas.sql`
3. Clic en **"Run"** (botón verde)

### 2.2 Obtener tus claves de Supabase
1. Ve a **Settings → API** (menú izquierdo)
2. Copia:
   - **Project URL** → algo como `https://xxxx.supabase.co`
   - **anon public key** → una clave larga

---

## PASO 3 — Configurar el proyecto en VS Code

### 3.1 Abrir la carpeta del proyecto
1. Abre VS Code
2. **File → Open Folder**
3. Selecciona la carpeta `distrinova/` que descargaste

### 3.2 Abrir la Terminal integrada
- Presiona **Ctrl + `** (la tecla del acento grave, arriba del Tab)
- O ve a **Terminal → New Terminal**

### 3.3 Crear entorno virtual (para aislar las librerías)
Escribe esto en la terminal, línea por línea:

```bash
# Crear entorno virtual
python -m venv venv

# Activarlo (Windows)
venv\Scripts\activate

# Activarlo (Mac/Linux)
source venv/bin/activate
```

Sabrás que funcionó cuando veas `(venv)` al inicio de la línea.

### 3.4 Instalar todas las librerías
Con el entorno activado, escribe:

```bash
pip install -r requirements.txt
```

Espera que termine (puede tardar 1-2 minutos).

---

## PASO 4 — Configurar las claves secretas

1. Abre el archivo `.env` en VS Code
2. Reemplaza los valores con tus datos de Supabase:

```
SUPABASE_URL=https://TU_URL_AQUI.supabase.co
SUPABASE_KEY=TU_CLAVE_ANON_AQUI
```

⚠️ **IMPORTANTE:** Nunca compartas este archivo ni lo subas a GitHub.

---

## PASO 5 — Ejecutar la aplicación

En la terminal de VS Code (con el entorno activado):

```bash
streamlit run app.py
```

Se abrirá automáticamente en tu navegador en:
**http://localhost:8501**

---

## PASO 6 — Publicar en internet (para compartir con tus compañeros)

### 6.1 Crear cuenta en GitHub
1. Ve a: https://github.com
2. Crea una cuenta gratuita

### 6.2 Subir el proyecto a GitHub
En la terminal de VS Code:

```bash
git init
git add .
git commit -m "DistriNova ERP - versión inicial"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/distrinova-erp.git
git push -u origin main
```

### 6.3 Publicar en Streamlit Cloud (GRATIS)
1. Ve a: https://share.streamlit.io
2. Inicia sesión con tu cuenta de GitHub
3. Clic en **"New app"**
4. Selecciona tu repositorio `distrinova-erp`
5. En "Main file path" escribe: `app.py`
6. En **"Advanced settings → Secrets"** pega:
   ```
   SUPABASE_URL = "https://TU_URL.supabase.co"
   SUPABASE_KEY = "TU_CLAVE"
   ```
7. Clic en **"Deploy!"**

En ~3 minutos tendrás un link como:
**https://distrinova-erp.streamlit.app**

¡Compártelo con Yoany, Gómez, Karen, Laura y Mafe! 🎉

---

## ❓ Errores comunes y soluciones

| Error | Solución |
|-------|----------|
| `python no se reconoce` | Reinstalar Python marcando "Add to PATH" |
| `pip no se reconoce` | Activar el entorno virtual primero |
| `ModuleNotFoundError` | Correr `pip install -r requirements.txt` de nuevo |
| La app no abre en el navegador | Ir manualmente a `http://localhost:8501` |
| Error de Supabase | Verificar URL y clave en el archivo `.env` |

---

## 📞 Estructura final de archivos

```
distrinova/
├── app.py                  ← Archivo principal (correr este)
├── database.py             ← Conexión a Supabase
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Planeador_Rutas.py
│   ├── 3_Cotizador.py
│   ├── 4_Inventario.py
│   ├── 5_Pedidos.py
│   ├── 6_Historial.py
│   └── 7_Documentos.py
├── .env                    ← Claves secretas (NO compartir)
├── requirements.txt        ← Librerías
└── supabase_tablas.sql     ← Script de base de datos
```
