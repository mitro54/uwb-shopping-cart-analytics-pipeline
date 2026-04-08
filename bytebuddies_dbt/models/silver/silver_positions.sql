{{ config(materialized='view') }}

WITH perus_puhdistus AS (
    -- 1. Silver-tason peruspuhdistus: laatu, rajat ja aukioloajat
    SELECT DISTINCT
        node_id,
        timestamp AS aika,
        x,
        y,
        q
    FROM {{ ref('bronze_csv_data') }}
    WHERE 
        q > 35 
        AND x IS NOT NULL 
        AND y IS NOT NULL
        -- Geofencing: Kaupan rajat (Maksimileveys 10406 cm, Maksimikorkeus 5220 cm)
        AND x >= 0 AND x <= 10406
        AND y >= 0 AND y <= 5220
        -- Ongelmalliset alueet (Latauspisteet 1 ja 2 pythagoraan säteellä pisteestä)
        AND (POWER(x - 100, 2) + POWER(y - 2500, 2)) > POWER(400, 2)  -- Turvaportit
        AND (POWER(x - 900, 2) + POWER(y - 3600, 2)) > POWER(600, 2)  -- Liukuportaat
        -- Aukioloajat schema.yml vaatimuksen mukaan
        AND EXTRACT('hour' FROM timestamp) >= 7
        AND EXTRACT('hour' FROM timestamp) <= 22
),
liikkeet AS (
    -- 2. Haetaan edellinen sijainti ja aika per kärry
    SELECT
        node_id,
        aika,
        x,
        y,
        q,
        LAG(x) OVER (PARTITION BY node_id ORDER BY aika) AS edellinen_x,
        LAG(y) OVER (PARTITION BY node_id ORDER BY aika) AS edellinen_y,
        LAG(aika) OVER (PARTITION BY node_id ORDER BY aika) AS edellinen_aika
    FROM perus_puhdistus
),
rikastettu AS (
    -- 3. Lasketaan matka ja aikaväli sekunteina
    SELECT
        *,
        -- Matka (Pythagoraan lause), muunnos senttimetreistä (1 yksikkö = 1cm) -> metreiksi (/ 100.0)
        SQRT(POWER(x - edellinen_x, 2) + POWER(y - edellinen_y, 2)) / 100.0 AS dist_m,
        DATE_DIFF('second', edellinen_aika, aika) AS sekuntia_edellisesta
    FROM liikkeet
),
jitter_suodatus AS (
    -- 4. Karsitaan yksittäiset Jitter-hypyt (Schema limit > 3.5 m/s)
    SELECT *
    FROM rikastettu
    WHERE sekuntia_edellisesta IS NULL 
       OR sekuntia_edellisesta = 0
       OR (dist_m / sekuntia_edellisesta) <= 3.5
),
sessiomerkinta AS (
    -- 5. Tunnistetaan pitkän viipymän jälkeinen session katkeaminen (SESSION_GAP_THRESHOLD = 900s / 15 min)
    SELECT
        *,
        CASE 
            WHEN edellinen_aika IS NULL OR sekuntia_edellisesta > 900 THEN 1 
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
    MD5(node_id || '_' || CAST(session_id AS VARCHAR)) AS full_session_id,
    dist_m,
    sekuntia_edellisesta,
    -- Nopeus (m/s)
    CASE 
        WHEN sekuntia_edellisesta > 0 THEN dist_m / sekuntia_edellisesta 
        ELSE 0 
    END AS speed_mps
FROM sessiot