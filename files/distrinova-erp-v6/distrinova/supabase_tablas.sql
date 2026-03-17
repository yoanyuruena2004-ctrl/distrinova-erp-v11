-- ============================================
-- DistriNova ERP v3.0 — Tablas Supabase
-- Pega esto en SQL Editor → Run
-- ============================================

CREATE TABLE IF NOT EXISTS inventario (
    id         SERIAL PRIMARY KEY,
    cedi       TEXT NOT NULL,
    stock      INTEGER DEFAULT 0,
    stock_min  INTEGER DEFAULT 50,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS movimientos (
    id           SERIAL PRIMARY KEY,
    cedi         TEXT NOT NULL,
    tipo         TEXT NOT NULL,
    cantidad     INTEGER NOT NULL,
    documento    TEXT,
    stock_result INTEGER,
    usuario      TEXT DEFAULT 'sistema',
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS despachos (
    id          SERIAL PRIMARY KEY,
    remision    TEXT UNIQUE,
    cedi_origen TEXT NOT NULL,
    destino     TEXT NOT NULL,
    km          NUMERIC,
    tortas      INTEGER NOT NULL,
    furgonetas  INTEGER NOT NULL,
    nocturno    BOOLEAN DEFAULT FALSE,
    costo_flete INTEGER NOT NULL,
    usuario     TEXT DEFAULT 'sistema',
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pedidos (
    id            SERIAL PRIMARY KEY,
    actor         TEXT NOT NULL,
    destino       TEXT NOT NULL,
    cantidad      INTEGER NOT NULL,
    precio_unit   INTEGER DEFAULT 0,
    total         INTEGER DEFAULT 0,
    observaciones TEXT,
    estado        TEXT DEFAULT 'Pendiente',
    usuario       TEXT DEFAULT 'sistema',
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facturas (
    id          SERIAL PRIMARY KEY,
    numero      TEXT UNIQUE,
    cliente     TEXT NOT NULL,
    nit         TEXT,
    cantidad    INTEGER,
    precio_unit INTEGER,
    costo_flete INTEGER DEFAULT 0,
    subtotal    INTEGER,
    iva         INTEGER,
    total       INTEGER,
    ruta        TEXT,
    usuario     TEXT DEFAULT 'Mafe',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ✅ NUEVA: tabla de lotes perecederos (FIFO)
CREATE TABLE IF NOT EXISTS lotes (
    id                 SERIAL PRIMARY KEY,
    lote_id            TEXT UNIQUE NOT NULL,
    cedi               TEXT NOT NULL,
    cantidad           INTEGER NOT NULL,
    fecha_ingreso      DATE NOT NULL,
    fecha_vencimiento  DATE NOT NULL,
    proveedor          TEXT,
    estado             TEXT DEFAULT 'activo',
    created_at         TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Datos iniciales
-- ============================================
INSERT INTO inventario (cedi, stock, stock_min) VALUES
    ('Medellín',    250, 100),
    ('Santa Rosa',   80,  40),
    ('Taraza',       90,  40)
ON CONFLICT DO NOTHING;

-- ============================================
-- Activar tiempo real
-- ============================================
ALTER PUBLICATION supabase_realtime ADD TABLE inventario;
ALTER PUBLICATION supabase_realtime ADD TABLE movimientos;
ALTER PUBLICATION supabase_realtime ADD TABLE despachos;
ALTER PUBLICATION supabase_realtime ADD TABLE pedidos;
ALTER PUBLICATION supabase_realtime ADD TABLE facturas;
ALTER PUBLICATION supabase_realtime ADD TABLE lotes;
