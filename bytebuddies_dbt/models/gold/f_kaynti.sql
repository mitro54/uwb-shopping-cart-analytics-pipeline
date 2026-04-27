WITH aggregoidut_sessiot AS (
    -- 1. Yhdistetään session datapisteet yhdeksi analytiikalle käyttökelpoiseksi "kauppareissuksi"
    SELECT
        full_session_id AS kaynti_id, 
        node_id,
        MIN(aika) AS alku,
        MAX(aika) AS loppu,
        
        -- Puretaan aika suoraan MIN(aika) -arvosta, jotta vältetään MIN(hour) -virheet.
        
        CAST(MIN(aika) AS DATE) AS kaynti_paiva,
        EXTRACT('hour' FROM MIN(aika)) AS kaynti_tunti,
        EXTRACT('isodow' FROM MIN(aika)) AS kaynti_viikonpaiva,
        
        DATE_DIFF('second', MIN(aika), MAX(aika)) AS kesto_sekunteina,
        COALESCE(SUM(dist_m), 0) AS matka,
        -- Haetaan session ensimmäisen datapisteen alku_x ja alku_y tarkistaaksemme sisääntuloalueen (REQUIRE_START_ZONE)
        COUNT(*) AS pisteita,
        MIN_BY(x, aika) AS aloitus_x,
        MIN_BY(y, aika) AS aloitus_y,
        -- Spatiaalisen hajonnan eli levittäytyvyyden (MIN_SPATIAL_SPREAD) mittaaminen senttimetreistä metreihih
        SQRT(POWER(MAX(x) - MIN(x), 2) + POWER(MAX(y) - MIN(y), 2)) / 100.0 AS levittaytyvyys_m
    FROM {{ ref('silver_positions') }}
    GROUP BY full_session_id, node_id
)

SELECT
    kaynti_id,
    node_id,
    alku,
    loppu,
    kaynti_paiva,
    kaynti_tunti,
    kaynti_viikonpaiva,
    kesto_sekunteina,
    matka,
    pisteita,
    levittaytyvyys_m,
    -- Koko asioinnin keskinopeus (m/s)
    CASE WHEN kesto_sekunteina > 0 THEN matka / kesto_sekunteina ELSE 0 END AS keskinopeus
FROM aggregoidut_sessiot
-- HUOM: Sessioiden filtteröinti (haamukärryt jne.) tehdään nykyään suoraan silver_positions -tasolla.
-- Tämä malli vain aggregoida datan asiointitasolle.