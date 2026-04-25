
-- =========================================================================
-- ⚙️ LAITTEISTODIAGNOSTIIKKA -ASETUKSET (Jinja Config)
-- =========================================================================

-- Laaturajat (liputetaan, muttei poisteta)
{% set q_threshold = 35 %}
{% set max_x = 10406 %}
{% set max_y = 5220 %}

-- Aukioloajat (tunnit)
{% set shop_open = 7 %}
{% set shop_close = 22 %}

-- Maksiminopeus m/s (Jitter-liputus)
{% set max_jump_speed = 3.5 %}


-- =========================================================================
-- 🛠️ SQL-LOGIIKKA
-- =========================================================================

WITH liikkeet AS (
    SELECT
        node_id,
        timezone('{{ var("timezone") }}', timestamp::TIMESTAMPTZ) AS aika,
        x,
        y,
        q,
        -- Haetaan edelliset koordinaatit
        LAG(x) OVER (PARTITION BY node_id ORDER BY timestamp) AS edellinen_x,
        LAG(y) OVER (PARTITION BY node_id ORDER BY timestamp) AS edellinen_y,
        LAG(timestamp) OVER (PARTITION BY node_id ORDER BY timestamp) AS edellinen_aika
    FROM {{ ref('bronze_csv_data') }}
    WHERE x IS NOT NULL AND y IS NOT NULL
    {{ get_exclusion_zones() }}
),
rikastettu AS (
    SELECT
        *,
        -- Matka (Pythagoraan lause), muunnos senttimetreistä -> metreiksi
        SQRT(POWER(x - edellinen_x, 2) + POWER(y - edellinen_y, 2)) / 100.0 AS dist_m,
        DATE_DIFF('second', edellinen_aika, aika) AS sekuntia_edellisesta
    FROM liikkeet
),
nopeus_laskettu AS (
    SELECT
        *,
        -- Nopeus (m/s)
        CASE 
            WHEN sekuntia_edellisesta > 0 THEN dist_m / sekuntia_edellisesta 
            ELSE 0 
        END AS speed_mps
    FROM rikastettu
)

SELECT
    node_id,
    aika,
    CAST(aika AS DATE) AS dt,
    EXTRACT('hour' FROM aika) AS hour,
    x,
    y,
    q,
    speed_mps,
    sekuntia_edellisesta,
    
    -- Laitteistodiagnostiikan olennaiset TAGIT analytiikkaan
    -- 1. Heikko signaali (kyllä/ei)
    CASE WHEN q < {{ q_threshold }} THEN 1 ELSE 0 END AS is_low_quality,
    
    -- 2. Seinien ulkopuolella eksyminen (kyllä/ei)
    CASE WHEN x < 0 OR x > {{ max_x }} OR y < 0 OR y > {{ max_y }} THEN 1 ELSE 0 END AS is_out_of_bounds,
    
    -- 3. Jitter eli epäfysikaalinen hyppy (kyllä/ei)
    CASE WHEN speed_mps > {{ max_jump_speed }} THEN 1 ELSE 0 END AS is_jitter,

    -- 4. Kaupan aukioloaikojen ulkopuolella (Yöaika)
    CASE WHEN EXTRACT('hour' FROM aika) < {{ shop_open }} OR EXTRACT('hour' FROM aika) > {{ shop_close }} THEN 1 ELSE 0 END AS is_night_time

FROM nopeus_laskettu
