{{ config(
    materialized='table',
    post_hook=[
        "CREATE UNIQUE INDEX IF NOT EXISTS pk_f_osastokaynti ON {{ this }} (kaynti_id, osasto_id, osasto_sisaantulo)",
        "CREATE INDEX IF NOT EXISTS idx_osasto_id ON {{ this }} (osasto_id)"
    ]
) }}

-- Rakennetaan osastovierailut yhdistämällä puhdistetut koordinaatit osastojen laatikkorajoihin
WITH vierailut AS (
    SELECT
        s.full_session_id AS kaynti_id,
        s.node_id,
        o.osasto_id,
        o.nimi AS osaston_nimi,
        s.aika,
        s.sekuntia_edellisesta,
        s.dist_m
    FROM {{ ref('silver_positions') }} s
    INNER JOIN {{ ref('dim_osastot') }} o
        ON s.x >= o.alku_x AND s.x <= o.loppu_x
       AND s.y >= o.alku_y AND s.y <= o.loppu_y
)

SELECT
    kaynti_id,
    node_id,
    osasto_id,
    osaston_nimi,
    MIN(aika) AS osasto_sisaantulo,
    MAX(aika) AS osasto_poistuminen,
    DATE_DIFF('second', MIN(aika), MAX(aika)) AS vietetty_aika_sekunteina,
    COALESCE(SUM(dist_m), 0) AS matka_osastolla_m,
    COUNT(*) AS havainnot_osastolla
FROM vierailut
GROUP BY kaynti_id, node_id, osasto_id, osaston_nimi
ORDER BY kaynti_id, osasto_sisaantulo
