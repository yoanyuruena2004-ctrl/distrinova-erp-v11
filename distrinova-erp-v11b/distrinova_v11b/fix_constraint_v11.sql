-- ══════════════════════════════════════════════════════════════
-- DistriNova ERP v11 — Fix error "ordenes_servicio_tipo_orden_check"
-- Ejecutar en Supabase → SQL Editor
-- ══════════════════════════════════════════════════════════════

-- El error ocurre porque el tipo 'recoleccion_fabricante' no estaba
-- en el CHECK CONSTRAINT original de la tabla ordenes_servicio.

-- PASO 1: Eliminar el constraint antiguo
ALTER TABLE ordenes_servicio
  DROP CONSTRAINT IF EXISTS ordenes_servicio_tipo_orden_check;

-- PASO 2: Agregar el constraint actualizado con TODOS los tipos de v11
ALTER TABLE ordenes_servicio
  ADD CONSTRAINT ordenes_servicio_tipo_orden_check
  CHECK (tipo_orden IN (
    'recoleccion',           -- 🔴 Recolección MP: Proveedor → CEDI
    'recoleccion_fabricante',-- 🟣 Recolección PT: Fabricante → CEDI  ← NUEVO v11
    'transferencia',         -- 🔵 Transferencia: CEDI → CEDI
    'entrega_cedi',          -- 🟠 Entrega a CEDI: CEDI → Bodega cliente
    'entrega_directa'        -- 🟢 Entrega Directa: CEDI → Cliente final
  ));

-- VERIFICACIÓN: confirma que el constraint quedó bien
SELECT conname, consrc
FROM pg_constraint
WHERE conname = 'ordenes_servicio_tipo_orden_check';
