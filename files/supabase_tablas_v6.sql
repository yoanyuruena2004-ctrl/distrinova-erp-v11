-- ============================================================
-- DistriNova ERP v6.0 — NUEVAS TABLAS (ejecutar en Supabase SQL Editor)
-- Solo las tablas NUEVAS — las anteriores ya existen
-- ============================================================

-- Tabla de rutas dinámicas (reemplaza las fijas en código)
CREATE TABLE IF NOT EXISTS rutas (
    id          SERIAL PRIMARY KEY,
    municipio   TEXT UNIQUE NOT NULL,
    km          NUMERIC NOT NULL,
    tiempo_est  TEXT DEFAULT '—',
    salida_max  TEXT DEFAULT '03:00',
    lat         NUMERIC,
    lon         NUMERIC,
    activa      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Tabla de vehículos
CREATE TABLE IF NOT EXISTS vehiculos (
    id          SERIAL PRIMARY KEY,
    codigo      TEXT UNIQUE NOT NULL,
    tipo        TEXT DEFAULT 'Furgoneta',
    ancho_m     NUMERIC DEFAULT 2.2,
    largo_m     NUMERIC DEFAULT 2.5,
    alto_m      NUMERIC DEFAULT 1.8,
    arrume_max  INTEGER DEFAULT 3,
    caja_ancho  NUMERIC DEFAULT 0.30,
    caja_largo  NUMERIC DEFAULT 0.30,
    caja_alto   NUMERIC DEFAULT 0.15,
    capacidad   INTEGER,   -- calculado automáticamente
    tarifa_km   INTEGER DEFAULT 3000,
    estado      TEXT DEFAULT 'Activo',
    notas       TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Historial de conversaciones del agente IA
CREATE TABLE IF NOT EXISTS ia_chat (
    id          SERIAL PRIMARY KEY,
    usuario     TEXT NOT NULL,
    rol         TEXT NOT NULL,  -- 'user' o 'assistant'
    mensaje     TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Datos iniciales — rutas
INSERT INTO rutas (municipio, km, tiempo_est, salida_max, lat, lon) VALUES
    ('Santa Rosa de Osos', 77.4,  '1h 20m', '03:40', 6.6458, -75.4627),
    ('Yarumal',            122.4, '2h 10m', '02:50', 7.0025, -75.5147),
    ('Valdivia',           174.0, '3h 00m', '02:00', 7.1692, -75.4397),
    ('Taraza',             249.0, '4h 10m', '00:50', 7.5731, -75.4058),
    ('Caucasia',           283.0, '4h 45m', '00:15', 7.9887, -75.1973)
ON CONFLICT (municipio) DO NOTHING;

-- Datos iniciales — vehículos
INSERT INTO vehiculos (codigo, tipo, ancho_m, largo_m, alto_m, arrume_max, capacidad, tarifa_km, estado) VALUES
    ('FRG-01', 'Furgoneta', 2.2, 2.5, 1.8, 3, 168, 3000, 'Activo'),
    ('FRG-02', 'Furgoneta', 2.2, 2.5, 1.8, 3, 168, 3000, 'Activo'),
    ('FRG-03', 'Furgoneta', 2.2, 2.5, 1.8, 3, 168, 3000, 'Activo'),
    ('FRG-04', 'Furgoneta', 2.2, 2.5, 1.8, 3, 168, 3000, 'Reserva')
ON CONFLICT (codigo) DO NOTHING;

ALTER PUBLICATION supabase_realtime ADD TABLE rutas;
ALTER PUBLICATION supabase_realtime ADD TABLE vehiculos;
ALTER PUBLICATION supabase_realtime ADD TABLE ia_chat;
