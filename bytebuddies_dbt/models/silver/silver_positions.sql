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

        -- NEW: Rectangular Exclusions (Removing "outside" areas)
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
            ELSE 0 
        END AS is_new_session
    FROM jitter_suodatus
),
sessiot AS (
    -- 6. Kumulatiivinen summa is_new_session-arvoista muodostaa yksilöllisen session numeron
    SELECT
        *,
        SUM(is_new_session) OVER (PARTITION BY node_id ORDER BY aika) AS session_id
    FROM sessiomerkinta
)

SELECT
    node_id,
    aika,
    x,
    y,
    q,
    session_id,
    -- Luodaan MD5-hash full_session_id:ksi schema.yml vaatimuksen mukaan
    MD5(node_id || '_' || CAST(session_id AS VARCHAR)) AS full_session_id,
    EXTRACT('hour' FROM aika) AS hour,
    EXTRACT('isodow' FROM aika) AS weekday,
    dist_m,
    sekuntia_edellisesta,
    -- Nopeus (m/s)
    CASE 
        WHEN sekuntia_edellisesta > 0 THEN dist_m / sekuntia_edellisesta 
        ELSE 0 
    END AS speed_mps
FROM sessiot