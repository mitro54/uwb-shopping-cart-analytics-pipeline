-- =========================================================================
-- ⚙️ TUOTANTOTASON DATAN SIIVOUS -ASETUKSET (Jinja Config)
-- =========================================================================

-- (Konfiguraatio luetaan dbt_project.yml:n vars-osiosta)

-- =========================================================================
-- 🛠️ SQL-LOGIIKKA
-- =========================================================================

WITH perus_puhdistus AS (
    -- 1. Silver-tason peruspuhdistus: laatu, rajat, aukioloajat ja KASSA-ALUEEN TUNNISTUS
    SELECT DISTINCT
        node_id,
        timestamp AS aika,
        x,
        y,
        q,
        -- Määritetään, onko piste kassa-alueella
        CASE 
            WHEN x >= {{ var('checkout_x_min') }} AND x <= {{ var('checkout_x_max') }} 
             AND y >= {{ var('checkout_y_min') }} AND y <= {{ var('checkout_y_max') }} THEN 1 
            ELSE 0 
        END AS in_checkout
    FROM {{ ref('bronze_csv_data') }}
    WHERE 
        q > {{ var('q_threshold', 35) }} 
        AND x IS NOT NULL 
        AND y IS NOT NULL
        -- Geofencing: Kaupan rajat
        AND x >= 0 AND x <= {{ var('max_x_cm') }}
        AND y >= 0 AND y <= {{ var('max_y_cm') }}
        -- Ongelmalliset alueet (Latauspisteet 1 ja 2 pythagoraan säteellä pisteestä)
        AND (POWER(x - {{ var('prob1_x') }}, 2) + POWER(y - {{ var('prob1_y') }}, 2)) > POWER({{ var('prob1_r') }}, 2)
        AND (POWER(x - {{ var('prob2_x') }}, 2) + POWER(y - {{ var('prob2_y') }}, 2)) > POWER({{ var('prob2_r') }}, 2)
        -- Aukioloajat schema.yml vaatimuksen mukaan
        AND EXTRACT('hour' FROM timestamp) >= {{ var('shop_open') }}
        AND EXTRACT('hour' FROM timestamp) <= {{ var('shop_close') }}

        -- 1. y > 30 and x between 0 and 15
        AND NOT (y > 3000 AND x >= 0 AND x <= 1500)
        
        -- 2. y between 0 and 6 and x > 84
        AND NOT (y >= 0 AND y <= 600 AND x > 8400)
        
        -- 3. y > 47 and x > 99
        AND NOT (y > 4700 AND x > 9900)

),
liikkeet AS (
    -- 2. Haetaan edellinen sijainti, aika ja kassatieto per kärry
    SELECT
        node_id,
        aika,
        x,
        y,
        q,
        in_checkout,
        LAG(x) OVER (PARTITION BY node_id ORDER BY aika) AS edellinen_x,
        LAG(y) OVER (PARTITION BY node_id ORDER BY aika) AS edellinen_y,
        LAG(aika) OVER (PARTITION BY node_id ORDER BY aika) AS edellinen_aika,
        -- Tarkistetaan oliko kärry edellisellä kerralla kassalla
        LAG(in_checkout) OVER (PARTITION BY node_id ORDER BY aika) AS edellinen_in_checkout
    FROM perus_puhdistus
),
rikastettu AS (
    -- 3. Lasketaan matka ja aikaväli sekunteina
    SELECT
        *,
        -- Matka (Pythagoraan lause), muunnos senttimetreistä -> metreiksi
        COALESCE(SQRT(POWER(x - edellinen_x, 2) + POWER(y - edellinen_y, 2)) / 100.0, 0) AS dist_m,
        COALESCE(DATE_DIFF('second', edellinen_aika, aika), 0) AS sekuntia_edellisesta
    FROM liikkeet
),
jitter_suodatus AS (
    -- 4. Karsitaan yksittäiset Jitter-hypyt
    SELECT *
    FROM rikastettu
    WHERE sekuntia_edellisesta IS NULL 
       OR sekuntia_edellisesta = 0
       OR (dist_m / sekuntia_edellisesta) <= {{ var('max_jump_speed', 3.5) }}
),
sessiomerkinta AS (
    -- 5. Tunnistetaan uusi sessio: pitkä viipymä TAI kassoilta poistuminen
    SELECT
        *,
        CASE 
            -- Aikaero ylittää kynnyksen tai ensimmäinen rivi
            WHEN edellinen_aika IS NULL OR sekuntia_edellisesta > {{ var('session_gap_threshold', 900) }} THEN 1 
            -- Kärry poistui kassa-alueelta (edellinen piste kassalla, uusi ei ole)
            WHEN in_checkout = 0 AND edellinen_in_checkout = 1 THEN 1
            -- Kärry teki fyysisesti mahdottoman hypyn (> 15m) -> Katkaistaan sessio
            WHEN dist_m > 15.0 THEN 1
            ELSE 0 
        END AS is_new_session
    FROM jitter_suodatus
),
sessiot_raaka AS (
    -- 6. Kumulatiivinen summa muodostaa sessiot
    SELECT
        *,
        SUM(is_new_session) OVER (PARTITION BY node_id ORDER BY aika) AS session_id
    FROM sessiomerkinta
),
sessiot_metadata AS (
    -- 7. Lisätään full_session_id ja perustiedot
    SELECT
        *,
        MD5(node_id || '_' || CAST(session_id AS VARCHAR)) AS full_session_id,
        EXTRACT('hour' FROM aika) AS hour,
        EXTRACT('isodow' FROM aika) AS weekday,
        CASE 
            WHEN sekuntia_edellisesta > 0 THEN dist_m / sekuntia_edellisesta 
            ELSE 0 
        END AS speed_mps
    FROM sessiot_raaka
),
stationary_detector AS (
    -- 8. PAIKALLAANOLO-LEIKKURI (Stationary Cutter)
    -- Etsitään pisteet, joista alkaa vähintään 20 minuutin paikallaanolo
    SELECT
        *,
        -- Lasketaan 20 minuutin forward-windowin bounding box
        MAX(x) OVER w_20m - MIN(x) OVER w_20m AS spread_x,
        MAX(y) OVER w_20m - MIN(y) OVER w_20m AS spread_y,
        MAX(aika) OVER w_20m AS window_end_time,
        COUNT(*) OVER w_20m AS window_points
    FROM sessiot_metadata
    WINDOW w_20m AS (
        PARTITION BY full_session_id 
        ORDER BY aika 
        RANGE BETWEEN CURRENT ROW AND INTERVAL '{{ var("stationary_timeout_min") }}' MINUTE FOLLOWING
    )
),
stationary_flags AS (
    -- Liputetaan pisteet, joista alkaa hylkäys (diagonaali < ~7m eli radius 5m)
    SELECT
        *,
        CASE 
            WHEN DATEDIFF('second', aika, window_end_time) >= {{ var("stationary_timeout_min") * 60 }}
             AND SQRT(POWER(spread_x, 2) + POWER(spread_y, 2)) < {{ var("stationary_radius_m") * 100 * 2.0 }}
            THEN 1 ELSE 0 
        END AS is_stationary_start
    FROM stationary_detector
),
session_cutoffs AS (
    -- Etsitään ensimmäinen hylkäyspiste per sessio
    SELECT
        full_session_id,
        MIN(CASE WHEN is_stationary_start = 1 THEN aika ELSE '9999-12-31'::TIMESTAMP END) AS cutoff_time
    FROM stationary_flags
    GROUP BY full_session_id
),
sessiot_leikattu AS (
    -- Leikataan sessiot cutoff-ajan kohdalta (säilytetään alku)
    SELECT f.*
    FROM stationary_flags f
    JOIN session_cutoffs c ON f.full_session_id = c.full_session_id
    WHERE f.aika <= c.cutoff_time
),
session_point_metadata AS (
    -- 9. LASKETAAN PISTEKOHTAISET RIVEITÄ KOSKEVAT TIEDOT (Window functions tässä)
    SELECT
        *,
        -- Järjestysnumerot alusta ja lopusta
        ROW_NUMBER() OVER (PARTITION BY full_session_id ORDER BY aika) AS rnk_start,
        ROW_NUMBER() OVER (PARTITION BY full_session_id ORDER BY aika DESC) AS rnk_back
    FROM sessiot_leikattu
),
session_validation_base AS (
    -- 10. KERÄTÄÄN TUNNUSLUVUT LOPULLISTA VALIDIOINTIA VARTEN
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
    FROM session_point_metadata
    GROUP BY full_session_id
),
valid_sessions AS (
    -- 11. LOPULLINEN SUODATUS (Vastaten notebookin clean_data)
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

-- LOPPUTULOS: Vain validit sessiot, leikattuna ja kassa-alue poistettuna (visualisoinnin siistimiseksi)
SELECT * EXCLUDE(spread_x, spread_y, window_end_time, window_points, is_stationary_start, rnk_start, rnk_back)
FROM session_point_metadata
WHERE full_session_id IN (SELECT full_session_id FROM valid_sessions)
  AND in_checkout = 0