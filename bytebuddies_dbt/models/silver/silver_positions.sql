
-- =========================================================================
-- ⚙️ TUOTANTOTASON DATAN SIIVOUS -ASETUKSET (Jinja Config)
-- =========================================================================

-- Laatu ja rajat
{% set q_threshold = 35 %}
{% set max_x = 10406 %}
{% set max_y = 5220 %}

-- Aukioloajat (tunnit)
{% set shop_open = 7 %}
{% set shop_close = 22 %}

-- Ongelmalliset alueet (x, y, säde senttimetreinä)
{% set prob1_x = 100 %}{% set prob1_y = 2500 %}{% set prob1_r = 400 %}  -- Turvaportit
{% set prob2_x = 900 %}{% set prob2_y = 3600 %}{% set prob2_r = 600 %}  -- Liukuportaat

-- Alue-määritykset (Geofencing / Kassa-alue)
{% set checkout_x_min = 0 %}{% set checkout_x_max = 2000 %}
{% set checkout_y_min = 4000 %}{% set checkout_y_max = 5220 %}

-- Sessiologiikka ja fysiologiset rajat
{% set session_gap_threshold = 900 %}  -- Signaalikatkos sekunteina (15 min)
{% set max_jump_speed = 3.5 %}         -- Maksiminopeus m/s (Jitter-suodatus)

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
            WHEN x >= {{ checkout_x_min }} AND x <= {{ checkout_x_max }} 
             AND y >= {{ checkout_y_min }} AND y <= {{ checkout_y_max }} THEN 1 
            ELSE 0 
        END AS in_checkout
    FROM {{ ref('bronze_csv_data') }}
    WHERE 
        q > {{ q_threshold }} 
        AND x IS NOT NULL 
        AND y IS NOT NULL
        -- Geofencing: Kaupan rajat
        AND x >= 0 AND x <= {{ max_x }}
        AND y >= 0 AND y <= {{ max_y }}
        -- Ongelmalliset alueet (Latauspisteet 1 ja 2 pythagoraan säteellä pisteestä)
        AND (POWER(x - {{ prob1_x }}, 2) + POWER(y - {{ prob1_y }}, 2)) > POWER({{ prob1_r }}, 2)
        AND (POWER(x - {{ prob2_x }}, 2) + POWER(y - {{ prob2_y }}, 2)) > POWER({{ prob2_r }}, 2)
        -- Aukioloajat schema.yml vaatimuksen mukaan
        AND EXTRACT('hour' FROM timestamp) >= {{ shop_open }}
        AND EXTRACT('hour' FROM timestamp) <= {{ shop_close }}
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
        SQRT(POWER(x - edellinen_x, 2) + POWER(y - edellinen_y, 2)) / 100.0 AS dist_m,
        DATE_DIFF('second', edellinen_aika, aika) AS sekuntia_edellisesta
    FROM liikkeet
),
jitter_suodatus AS (
    -- 4. Karsitaan yksittäiset Jitter-hypyt
    SELECT *
    FROM rikastettu
    WHERE sekuntia_edellisesta IS NULL 
       OR sekuntia_edellisesta = 0
       OR (dist_m / sekuntia_edellisesta) <= {{ max_jump_speed }}
),
sessiomerkinta AS (
    -- 5. Tunnistetaan uusi sessio: pitkä viipymä TAI kassoilta poistuminen
    SELECT
        *,
        CASE 
            -- Aikaero ylittää kynnyksen tai ensimmäinen rivi
            WHEN edellinen_aika IS NULL OR sekuntia_edellisesta > {{ session_gap_threshold }} THEN 1 
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
    CAST(aika AS DATE) AS dt,
    EXTRACT('hour' FROM aika) AS hour,
    EXTRACT('isodow' FROM aika) AS weekday,
    session_id,
    -- Luodaan MD5-hash full_session_id:ksi schema.yml vaatimuksen mukaan
    MD5(node_id || '_' || CAST(session_id AS VARCHAR)) AS full_session_id,
    dist_m,
    sekuntia_edellisesta,
    -- Nopeus (m/s)
    CASE 
        WHEN sekuntia_edellisesta > 0 THEN dist_m / sekuntia_edellisesta 
        ELSE 0 
    END AS speed_mps
FROM sessiot