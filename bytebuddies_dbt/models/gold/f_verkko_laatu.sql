-- =========================================================================
-- 📡 VERKON JA LAITTEISTON LAATU: KUUMUUSKARTTA (Heatmap)
-- =========================================================================

WITH grid_pyoristys AS (
    SELECT
        node_id,
        q,
        is_low_quality,
        is_jitter,
        x,
        y,
        -- Pyöristetään koordinaatit muodostamaan 1x1 metrin ruudukko (100cm grid)
        FLOOR(x / 100.0) * 100 AS grid_x,
        FLOOR(y / 100.0) * 100 AS grid_y
    FROM {{ ref('silver_device_diagnostics') }}
    -- Analysoidaan vain pisteet, jotka ylipäätään saatiin kaupan alueelta. (Jitter ja low_q saa olla).
    WHERE is_out_of_bounds = 0
      AND is_excluded_zone = 0
)

SELECT
    grid_x,
    grid_y,
    COUNT(*) AS total_pings,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY q), 1) AS median_quality,
    MIN(q) AS min_quality,
    SUM(is_low_quality) AS low_quality_pings,
    SUM(is_jitter) AS jitter_pings,
    -- Kuinka iso osa tämän ruudun pingauksista oli heikkolaatuisia?
    ROUND(SUM(is_low_quality) * 100.0 / NULLIF(COUNT(*), 0), 2) AS low_quality_pct
FROM grid_pyoristys
GROUP BY grid_x, grid_y
