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
        edellinen_x,
        edellinen_y,
        -- Pyöristetään koordinaatit muodostamaan 1x1 metrin ruudukko (100cm grid)
        FLOOR(x / 100.0) * 100 AS grid_x,
        FLOOR(y / 100.0) * 100 AS grid_y
    FROM {{ ref('silver_device_diagnostics') }}
    -- Analysoidaan vain pisteet, jotka ylipäätään saatiin kaupan alueelta. (Jitter ja low_q saa olla).
    WHERE is_out_of_bounds = 0
),

main_agg AS (
    SELECT
        grid_x,
        grid_y,
        COUNT(*) AS total_pings,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY q), 1) AS median_quality,
        MIN(q) AS min_quality,
        SUM(is_low_quality) AS low_quality_pings,
        ROUND(SUM(is_low_quality) * 100.0 / NULLIF(COUNT(*), 0), 2) AS low_quality_pct
    FROM grid_pyoristys
    GROUP BY grid_x, grid_y
),

-- Jitter lasketaan LÄHDESIJAINNIN mukaan — missä kärryn pingaus oli ENNEN hyppyä,
-- ei mihin se hypättyään päätyi. Näin heatmap osoittaa ongelman lähteen.
jitter_lahde AS (
    SELECT
        FLOOR(edellinen_x / 100.0) * 100 AS grid_x,
        FLOOR(edellinen_y / 100.0) * 100 AS grid_y,
        COUNT(*) AS jitter_pings
    FROM grid_pyoristys
    WHERE is_jitter = 1
      AND edellinen_x IS NOT NULL
      AND edellinen_y IS NOT NULL
    GROUP BY 1, 2
)

SELECT
    m.grid_x,
    m.grid_y,
    m.total_pings,
    m.median_quality,
    m.min_quality,
    m.low_quality_pings,
    m.low_quality_pct,
    COALESCE(j.jitter_pings, 0) AS jitter_pings,
    ROUND(COALESCE(j.jitter_pings, 0) * 100.0 / NULLIF(m.total_pings, 0), 2) AS jitter_pct
FROM main_agg m
LEFT JOIN jitter_lahde j ON m.grid_x = j.grid_x AND m.grid_y = j.grid_y
