{{ config(materialized='table') }}

-- =========================================================================
-- 🥇 GOLD: gold_reitit — Yksittäiseen reittiin liittyvät filtteröinnit
-- =========================================================================
-- Lähde  : silver_positions
-- Tavoite: Vain validit sessiot (oikeat kauppareissut), jotka alkavat 
-- sisäänkäynniltä ja päättyvät kassoille, ja täyttävät asioinnin minimivaatimukset.
-- =========================================================================

WITH session_validation_base AS (
    -- 1. KERÄTÄÄN TUNNUSLUVUT LOPULLISTA VALIDIOINTIA VARTEN
    SELECT
        full_session_id,
        MIN(aika) AS session_start,
        MAX(aika) AS session_end,
        SUM(dist_m) AS total_dist_m,
        COUNT(*) AS point_count,
        MIN(x) AS min_x,
        MAX(x) AS max_x,
        MIN(y) AS min_y,
        MAX(y) AS max_y,
        -- Aloituspisteen koordinaatit (haetaan rnk_start = 1 kohdalta)
        MAX(CASE WHEN rnk_start = 1 THEN x ELSE NULL END) AS first_x,
        MAX(CASE WHEN rnk_start = 1 THEN y ELSE NULL END) AS first_y,
        -- Päättyminen kassoille (tail 5)
        MAX(CASE WHEN rnk_back <= 5 AND in_checkout = 1 THEN 1 ELSE 0 END) AS ends_in_checkout
    FROM {{ ref('silver_positions') }}
    GROUP BY full_session_id
),
valid_sessions AS (
    -- 2. LOPULLINEN SUODATUS (Vastaten aiempaa silver_positions-logiikkaa)
    SELECT full_session_id
    FROM session_validation_base
    WHERE 
        -- Aloitus sisäänkäynniltä (metrit -> senttimetrit)
        first_x BETWEEN {{ var('start_zone_x_min') | float * 100 }} AND {{ var('start_zone_x_max') | float * 100 }}
        AND first_y BETWEEN {{ var('start_zone_y_min') | float * 100 }} AND {{ var('start_zone_y_max') | float * 100 }}
        -- Päättyminen kassoille
        AND ends_in_checkout = 1
        -- Fysiologiset ja liiketoiminnalliset rajat
        AND point_count >= {{ var('min_session_points') }}
        AND total_dist_m BETWEEN {{ var('min_session_dist_m') }} AND {{ var('max_session_dist_m') }}
        AND DATEDIFF('second', session_start, session_end) BETWEEN {{ var('min_session_time_s') }} AND {{ var('max_session_time_s') }}
        AND (total_dist_m / NULLIF(DATEDIFF('second', session_start, session_end), 0)) BETWEEN {{ var('min_avg_speed_mps') }} AND {{ var('max_avg_speed_mps') }}
        AND SQRT(POWER(max_x - min_x, 2) + POWER(max_y - min_y, 2)) >= {{ var('min_spatial_spread_m') | float * 100 }}
)

-- LOPPUTULOS: Vain validit sessiot, kassa-alue poistettuna (visualisoinnin siistimiseksi)
SELECT * EXCLUDE(rnk_start, rnk_back)
FROM {{ ref('silver_positions') }}
WHERE full_session_id IN (SELECT full_session_id FROM valid_sessions)
  AND in_checkout = 0
