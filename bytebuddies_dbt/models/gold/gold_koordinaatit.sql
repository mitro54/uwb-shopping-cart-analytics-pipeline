{{ config(materialized='table') }}

-- =========================================================================
-- 🥇 GOLD: gold_koordinaatit — Puhdistetut pysähdyskoordinaatit lämpökarttaan
-- =========================================================================
-- Lähde  : silver_positions
-- Tavoite: Yksi rivi per pysähdys, rikastettuna osastotiedolla.
-- =========================================================================

-- Vasen alakulma (Kärryt ja sisääntulo)
{% set noise_left_bottom_x_min = 0 %}
{% set noise_left_bottom_x_max = 1600 %}
{% set noise_left_bottom_y_min = 3000 %}
{% set noise_left_bottom_y_max = 5220 %}
-- UUSI: Vasemman reunan ylitursuava patti (punainen ympyräsi)
{% set noise_left_mid_x_min = 1600 %}
{% set noise_left_mid_x_max = 1900 %}
{% set noise_left_mid_y_min = 3000 %}
{% set noise_left_mid_y_max = 3600 %}
-- Oikean yläkulman laajennettu poisto (punainen ympyräsi: 8800 -> 8400)
{% set noise_top_right_x_min = 8400 %}
{% set noise_top_right_x_max = 10406 %}
{% set noise_top_right_y_min = 0 %}
{% set noise_top_right_y_max = 800 %}
-- Oikea alakulma
{% set noise_bottom_right_x_min = 9600 %}
{% set noise_bottom_right_x_max = 10406 %}
{% set noise_bottom_right_y_min = 4600 %}
{% set noise_bottom_right_y_max = 5220 %}
-- UUSI: Koko oikean reunan poisto (punainen viivasi, korvaa siirtokikan)
{% set noise_right_edge_x_min = 9700 %}
{% set noise_right_edge_x_max = 10406 %}
{% set noise_right_edge_y_min = 800 %}
{% set noise_right_edge_y_max = 4600 %}
-- Oikean reunan ghost-data siirretään vasemmalle
{% set ghost_right_x_min = 9700 %}
{% set ghost_right_x_max = 10406 %}
{% set ghost_right_y_min = 900 %}
{% set ghost_right_y_max = 4500 %}
{% set ghost_shift_left = 0 %}

WITH

pysahdykset_perus AS (
    SELECT
        MD5(node_id || '_' || CAST(aika AS VARCHAR)) AS pysahdys_id,
        full_session_id,
        node_id,
        aika AS start_time,
        aika AS end_time,
        sekuntia_edellisesta AS total_dwell_seconds,
        x,
        y,
        in_checkout
    FROM {{ ref('silver_positions') }}
    WHERE speed_mps <= 0.1
      AND sekuntia_edellisesta >= 0
      AND sekuntia_edellisesta <= 120  -- Maksimissaan 2 minuutin yksittäinen pysähdys
      AND in_checkout = 0
      AND dist_m <= 15.0  -- Suodatetaan pois yli 15m teleporttaukset
      AND EXTRACT(HOUR FROM aika) BETWEEN {{ var('shop_open') | float }} AND {{ var('shop_close') | float }}
),

pysahdykset AS (
    -- Poistetaan haamukärryt/kärryt jotka jätetty paikalleen (yli 3 tunnin kokonaisviipymä)
    SELECT *
    FROM pysahdykset_perus
    WHERE full_session_id IN (
        SELECT full_session_id
        FROM pysahdykset_perus
        GROUP BY full_session_id
        HAVING SUM(total_dwell_seconds) <= 10800
    )
),

puhdistettu AS (
    SELECT *
    FROM pysahdykset
    WHERE NOT (
        -- Vasen alakulma (sisääntulo/kärryt)
        (x BETWEEN {{ noise_left_bottom_x_min }} AND {{ noise_left_bottom_x_max }}
         AND y BETWEEN {{ noise_left_bottom_y_min }} AND {{ noise_left_bottom_y_max }})
        OR
        -- Vasen patti
        (x BETWEEN {{ noise_left_mid_x_min }} AND {{ noise_left_mid_x_max }}
         AND y BETWEEN {{ noise_left_mid_y_min }} AND {{ noise_left_mid_y_max }})
        OR
        -- Oikea yläkulma
        (x BETWEEN {{ noise_top_right_x_min }} AND {{ noise_top_right_x_max }}
         AND y BETWEEN {{ noise_top_right_y_min }} AND {{ noise_top_right_y_max }})
        OR
        -- Oikea alakulma
        (x BETWEEN {{ noise_bottom_right_x_min }} AND {{ noise_bottom_right_x_max }}
         AND y BETWEEN {{ noise_bottom_right_y_min }} AND {{ noise_bottom_right_y_max }})

    )
),

korjatut_koordinaatit AS (
    SELECT
        pysahdys_id,
        full_session_id,
        node_id,
        start_time,
        end_time,
        total_dwell_seconds,

        CASE
            WHEN x BETWEEN {{ ghost_right_x_min }} AND {{ ghost_right_x_max }}
             AND y BETWEEN {{ ghost_right_y_min }} AND {{ ghost_right_y_max }}
            THEN x - {{ ghost_shift_left }}
            ELSE x
        END AS x,

        y
    FROM puhdistettu
),

rikastettu AS (
    SELECT
        p.pysahdys_id,
        p.full_session_id,
        p.node_id,
        p.start_time,
        p.end_time,
        p.total_dwell_seconds,
        p.x,
        p.y,
        o.osasto_id,
        o.nimi AS osasto_nimi
    FROM korjatut_koordinaatit p
    LEFT JOIN {{ ref('dim_osastot') }} o
        ON p.x >= o.alku_x AND p.x <= o.loppu_x
       AND p.y >= o.alku_y AND p.y <= o.loppu_y
),

grid_aggregaatti AS (
    SELECT
        CAST(FLOOR(x / 100) * 100 AS INTEGER) AS grid_x,
        CAST(FLOOR(y / 100) * 100 AS INTEGER) AS grid_y,
        MODE(osasto_id)   AS osasto_id,
        MODE(osasto_nimi) AS osasto_nimi,
        SUM(total_dwell_seconds)           AS kokonaisviipyma_s,
        COUNT(*)                           AS pysahdysten_maara,
        COUNT(DISTINCT node_id)            AS uniikkeja_karrya,
        ROUND(AVG(total_dwell_seconds), 1) AS keskiviipyma_s
    FROM rikastettu
    GROUP BY grid_x, grid_y
)

SELECT
    grid_x,
    grid_y,
    osasto_id,
    osasto_nimi,
    kokonaisviipyma_s,
    pysahdysten_maara,
    uniikkeja_karrya,
    keskiviipyma_s
FROM grid_aggregaatti
WHERE kokonaisviipyma_s >= 30
ORDER BY kokonaisviipyma_s DESC