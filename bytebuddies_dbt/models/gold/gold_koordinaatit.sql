{{ config(materialized='table') }}

-- =========================================================================
-- 🥇 GOLD: f_koordinaatit — Puhdistetut pysähdyskoordinaatit lämpökarttaan
-- =========================================================================
-- Lähde  : silver_pysahdykset  (validoidut pysähdysjaksot, ei raa'at pingit)
-- Tavoite: Yksi rivi per pysähdys, rikastettuna osastotiedolla ja ilman
--          teknistä kohinaa. Optimoitu lämpökartta- ja reittvisualisointiin.
--
-- Poistettu alue (Vyöhyke 9 — Sisääntulo & kärryt):
--   x BETWEEN 0 AND 1200  AND  y BETWEEN 3500 AND 5200
--   Syy: Kärryjen säilytyspiste ja sisäänkäynti tuottavat teknistä kohinaa,
--        joka vääristää lämpökartan väriskaalan muulla myymäläalueella.
-- =========================================================================

{% set noise_x_min = 0    %}
{% set noise_x_max = 1200 %}
{% set noise_y_min = 3500 %}
{% set noise_y_max = 5200 %}

WITH

-- ---------------------------------------------------------------------------
-- I. LÄHDE — Haetaan validated pysähdysjaksot silveristä
-- ---------------------------------------------------------------------------
pysahdykset AS (
    SELECT
        pysahdys_id,
        full_session_id,
        node_id,
        start_time,
        end_time,
        total_dwell_seconds,
        x,
        y
    FROM {{ ref('silver_pysahdykset') }}
),

-- ---------------------------------------------------------------------------
-- II. SUODATUS — Poistetaan sisääntulon kohinaalue (Vyöhyke 9)
-- ---------------------------------------------------------------------------
puhdistettu AS (
    SELECT *
    FROM pysahdykset
    WHERE NOT (
        x BETWEEN {{ noise_x_min }} AND {{ noise_x_max }}
        AND y BETWEEN {{ noise_y_min }} AND {{ noise_y_max }}
    )
),

-- ---------------------------------------------------------------------------
-- III. RIKASTUS — Spatiaalinen liitos osastodimensioon
--      HUOM: LEFT JOIN säilyttää pysähdykset, jotka osuvat osastojen väliin
--            tai alueille joita ei ole kartoitettu (osasto_nimi = NULL).
-- ---------------------------------------------------------------------------
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
    FROM puhdistettu p
    LEFT JOIN {{ ref('dim_osastot') }} o
        ON p.x >= o.alku_x AND p.x <= o.loppu_x
       AND p.y >= o.alku_y AND p.y <= o.loppu_y
),

-- ---------------------------------------------------------------------------
-- IV. AGGREGOINTI — Lasketaan grid-tason kokonaisviipymä lämpökarttaa varten
--     Käytetään 100 cm (1 m) ruudukkoa: FLOOR(x / 100) * 100
-- ---------------------------------------------------------------------------
grid_aggregaatti AS (
    SELECT
        -- Pyöristetään koordinaatit lähimpään 100 cm ruutuun
        CAST(FLOOR(x / 100) * 100 AS INTEGER) AS grid_x,
        CAST(FLOOR(y / 100) * 100 AS INTEGER) AS grid_y,
        -- Säilytetään osastotieto (käytetään moodia, koska ruutu voi osua reunalle)
        MODE(osasto_id)   AS osasto_id,
        MODE(osasto_nimi) AS osasto_nimi,
        -- Kokonaisviipymä ruudussa — lämpökartan päämetriikka
        SUM(total_dwell_seconds)   AS kokonaisviipyma_s,
        COUNT(*)                   AS pysahdysten_maara,
        COUNT(DISTINCT node_id)    AS uniikkeja_karrya,
        AVG(total_dwell_seconds)   AS keskiviipyma_s
    FROM rikastettu
    GROUP BY grid_x, grid_y
)

-- ---------------------------------------------------------------------------
-- V. LOPPUTULOS — Gold-tason koordinaattitaulu
-- ---------------------------------------------------------------------------
SELECT
    grid_x,
    grid_y,
    osasto_id,
    osasto_nimi,
    kokonaisviipyma_s,
    pysahdysten_maara,
    uniikkeja_karrya,
    ROUND(keskiviipyma_s, 1) AS keskiviipyma_s
FROM grid_aggregaatti
ORDER BY kokonaisviipyma_s DESC
