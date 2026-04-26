-- =========================================================================
-- 🎯 PAIKANNUSTARKKUUS YÖAIKAISILLE PAIKALLAAN OLIJOILLE
-- =========================================================================
-- Grain: yksi rivi per laite (node_id) per yö (yo_paiva).
-- Tarkoitus: UWB-paikannusjärjestelmän tarkkuuden arviointi paikallaan
-- olevien laitteiden sijaintihajonnan perusteella.
-- Käyttäjä: paikannusyrityksen edustaja.
-- =========================================================================

WITH yopingit AS (
    SELECT
        node_id,
        aika                                                     AS aika_hki,
        x, y, q, is_low_quality, is_jitter,
        -- Yöpäivä = se ilta jona yö alkoi (22-tunti kuuluu tälle päivälle,
        -- 00-06 kuuluu edelliselle illalle)
        CAST(
            CASE
                WHEN EXTRACT('hour' FROM aika) < 7
                THEN CAST(aika AS DATE) - INTERVAL '1 day'
                ELSE CAST(aika AS DATE)
            END
        AS DATE) AS yo_paiva
    FROM {{ ref('silver_device_diagnostics') }}
    WHERE x IS NOT NULL AND y IS NOT NULL
      AND (
          EXTRACT('hour' FROM aika) >= 22
          OR EXTRACT('hour' FROM aika) < 7
      )
),

-- Ainoastaan laitteet jotka olivat paikallaan koko yön (>1000 pingiä)
paikallaan AS (
    SELECT node_id, yo_paiva
    FROM yopingit
    GROUP BY node_id, yo_paiva
    HAVING COUNT(*) > 10000
),

pingit AS (
    SELECT y.*
    FROM yopingit y
    INNER JOIN paikallaan p USING (node_id, yo_paiva)
),

-- Laske keskipiste ja regressiosuora per laite per yö
aggregaatti AS (
    SELECT
        node_id,
        yo_paiva,
        COUNT(*)                                        AS n_pings,
        AVG(x)                                          AS cx,
        AVG(y)                                          AS cy,
        STDDEV_POP(x)                                   AS std_x,
        STDDEV_POP(y)                                   AS std_y,
        -- Drift: regressiosuoran kulmakerroin (cm/s → cm/h)
        REGR_SLOPE(x, EPOCH(aika_hki)) * 3600.0        AS drift_x_cmh,
        REGR_SLOPE(y, EPOCH(aika_hki)) * 3600.0        AS drift_y_cmh,
        AVG(q)                                          AS avg_q,
        SUM(is_low_quality) * 100.0 / COUNT(*)          AS low_quality_pct
    FROM pingit
    GROUP BY node_id, yo_paiva
),

-- Laske etäisyydet keskipisteestä ja askelvirheet (jitter)
etaisyydet AS (
    SELECT
        p.node_id,
        p.yo_paiva,
        SQRT(POWER(p.x - a.cx, 2) + POWER(p.y - a.cy, 2)) AS dist,
        SQRT(
            POWER(p.x - LAG(p.x) OVER (PARTITION BY p.node_id, p.yo_paiva ORDER BY p.aika_hki), 2) +
            POWER(p.y - LAG(p.y) OVER (PARTITION BY p.node_id, p.yo_paiva ORDER BY p.aika_hki), 2)
        ) AS step_dist
    FROM pingit p
    JOIN aggregaatti a USING (node_id, yo_paiva)
)

SELECT
    a.yo_paiva,
    a.node_id,
    a.n_pings,
    ROUND(a.cx,  1)                                                             AS centroid_x,
    ROUND(a.cy,  1)                                                             AS centroid_y,
    ROUND(a.std_x, 1)                                                           AS std_x,
    ROUND(a.std_y, 1)                                                           AS std_y,
    ROUND(SQRT(a.std_x * a.std_x + a.std_y * a.std_y), 1)                      AS rmse_2d,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY e.dist), 1)              AS cep50,
    ROUND(PERCENTILE_CONT(0.68) WITHIN GROUP (ORDER BY e.dist), 1)              AS cep68,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY e.dist), 1)              AS cep95,
    ROUND(AVG(e.step_dist), 1)                                                  AS jitter_ka_cm,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY e.step_dist), 1)         AS jitter_p95_cm,
    ROUND(a.drift_x_cmh, 2)                                                     AS drift_x_cmh,
    ROUND(a.drift_y_cmh, 2)                                                     AS drift_y_cmh,
    ROUND(
        SUM(CASE WHEN e.dist > 2 * SQRT(a.std_x * a.std_x + a.std_y * a.std_y)
                 THEN 1 ELSE 0 END)
        * 100.0 / NULLIF(a.n_pings, 0), 1
    )                                                                           AS outlier_pct,
    ROUND(a.avg_q, 1)                                                           AS avg_q,
    ROUND(a.low_quality_pct, 1)                                                 AS low_quality_pct

FROM etaisyydet e
JOIN aggregaatti a USING (node_id, yo_paiva)
WHERE 
    -- Suodatetaan haamuvaunut, joiden keskipiste on rajojen ulkopuolella
    a.cx >= 0 AND a.cx <= {{ var('max_x_cm') }}
    AND a.cy >= 0 AND a.cy <= {{ var('max_y_cm') }}
    -- Suodatetaan myös laajennetut poissuljetut alueet (margin 200 cm), jotta jitter-vuodot poistuvat
    AND NOT (a.cx <= 700 AND a.cy >= 1950 AND a.cy <= 3200)
    AND NOT (a.cx >= 650 AND a.cx <= 1150 AND a.cy >= 3350 AND a.cy <= 3850)
    AND NOT (a.cx <= 1700 AND a.cy >= 2800)
    AND NOT (a.cx >= 8200 AND a.cy <= 800)
    AND NOT (a.cx >= 9700 AND a.cy >= 4500)
GROUP BY
    a.yo_paiva, a.node_id, a.n_pings,
    a.cx, a.cy, a.std_x, a.std_y,
    a.drift_x_cmh, a.drift_y_cmh,
    a.avg_q, a.low_quality_pct
ORDER BY a.yo_paiva, a.node_id
