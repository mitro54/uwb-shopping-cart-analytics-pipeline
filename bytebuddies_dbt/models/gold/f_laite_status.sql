-- =========================================================================
-- 🛒 LAITEKOHTAISTEN ONGELMIEN AGGREGOINTI (Päivätasolla)
-- =========================================================================

SELECT
    node_id,
    dt AS pvm,
    COUNT(*) AS total_pings,
    SUM(is_low_quality) AS weak_signals,
    SUM(is_out_of_bounds) AS out_of_bounds_pings,
    SUM(is_jitter) AS jumps,
    SUM(is_night_time) AS nighttime_pings,

    -- Laitteen keskimääräinen signaali päivän aikana
    ROUND(AVG(q), 1) AS avg_q,

    -- KPI: Ongelmaprosentti (Kuinka monessa pingissä oli jotain vikaa)
    ROUND(SUM(CASE WHEN is_low_quality = 1 OR is_out_of_bounds = 1 OR is_jitter = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS error_rate_pct

FROM {{ ref('silver_device_diagnostics') }}
GROUP BY node_id, dt
