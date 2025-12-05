-- Script para vincular los 35 productos a la Caja 3 (Cafe Britt)
-- Primero, aseguramos que los productos estén en la tabla vta_productos.
-- Si ya ejecutaste el INSERT, este paso no es necesario, pero verifica que no haya duplicados.

-- Vincular productos a la Caja 3 (asumiendo id_caja = 3)
INSERT INTO sistemas.vta_catalogo_porcaja (id_caja, id_prod)
SELECT 3, id_prod 
FROM sistemas.vta_productos 
WHERE descripcion_prod IN (
    '021129039','020200017','020200019','021112017',
    '021112057','021112059','021130111','021130066',
    '021130005','021130010','021130021','021130062',
    '021130093','020901011','020901012','020911110',
    '020911132','020911130','020227013','021004049',
    '021004050','021004051','021004052','021004053',
    '021004054','021004055','021004056','021004057',
    '021004058','021004059','021004060','021004061',
    '021004062','021004063','021004064'
)
AND id_prod NOT IN (
    SELECT id_prod FROM sistemas.vta_catalogo_porcaja WHERE id_caja = 3
);

-- Consulta para verificar cuántos productos hay vinculados a la caja 3 de esta lista
SELECT COUNT(*) as total_vinculados
FROM sistemas.vta_catalogo_porcaja cp
JOIN sistemas.vta_productos p ON cp.id_prod = p.id_prod
WHERE cp.id_caja = 3 
AND p.descripcion_prod IN (
    '021129039','020200017','020200019','021112017',
    '021112057','021112059','021130111','021130066',
    '021130005','021130010','021130021','021130062',
    '021130093','020901011','020901012','020911110',
    '020911132','020911130','020227013','021004049',
    '021004050','021004051','021004052','021004053',
    '021004054','021004055','021004056','021004057',
    '021004058','021004059','021004060','021004061',
    '021004062','021004063','021004064'
);
