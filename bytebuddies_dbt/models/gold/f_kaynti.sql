WITH aggregoidut_sessiot AS (
    -- 1. Yhdistetään session datapisteet yhdeksi analytiikalle käyttökelpoiseksi "kauppareissuksi"
    SELECT
        full_session_id AS kaynti_id, 
        node_id,
        MIN(aika) AS alku,
        MAX(aika) AS loppu,
        MIN(dt) AS kaynti_paiva,
        MIN(hour) AS kaynti_tunti,
        MIN(weekday) AS kaynti_viikonpaiva,
        DATE_DIFF('second', MIN(aika), MAX(aika)) AS kesto_sekunteina,
        COALESCE(SUM(dist_m), 0) AS matka,
        COUNT(*) AS pisteita,
        -- Haetaan session ensimmäisen datapisteen alku_x ja alku_y tarkistaaksemme sisääntuloalueen (REQUIRE_START_ZONE)
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
WHERE 
    -- 2. Tuotantotason armoton filtteri hylätyille ja haamukärryille (Gold Logic)
    kesto_sekunteina >= 180 AND kesto_sekunteina <= 14400             -- Aika: 3 min (180s) - 4 tuntia
    AND matka >= 30.0 AND matka <= 8000.0                             -- Matka: vähintään 30 metriä, max 8km
    AND (matka / NULLIF(kesto_sekunteina, 0)) >= 0.08                 -- MIN Keskinopeus
    AND (matka / NULLIF(kesto_sekunteina, 0)) <= 1.5                  -- MAX Keskinopeus
    AND pisteita >= 30                                                -- Vähintään "aidon asioinnin" vaatima pistekertymä
    AND levittaytyvyys_m >= 15.0                                      -- Reitin pitää levittyä myymälässä selvästi
    -- Vaaditaan että ensimmäinen havainto on sisääntulolta (START_ZONE)
    AND aloitus_x >= 0 AND aloitus_x <= 1200
    AND aloitus_y >= 0 AND aloitus_y <= 5220