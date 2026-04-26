-- =========================================================================
-- 🛒 HYLÄTYT KÄRRYT
-- =========================================================================
-- Grain: Yksi rivi per hylätty kärry per päivä (per aikaisin 2-tunnin aikaikkuna).
-- Tarkoitus: Tunnistaa kärryt jotka ovat olleet paikallaan yli 2h päiväaikaan
-- kaupan sisällä (latausasemat ja sisäänkäyntialue poissuljettuna data putkessa).
-- =========================================================================

WITH per_tunti AS (
    -- 1. Etsitään mediaanisijainti per kärry per tunti
    SELECT 
        node_id, 
        CAST(aika AS DATE) AS paiva,
        DATE_TRUNC('hour', aika) AS tunti,
        MEDIAN(x) AS med_x, 
        MEDIAN(y) AS med_y, 
        COUNT(*) AS pings
    FROM {{ ref('silver_positions') }}
    GROUP BY node_id, paiva, tunti
    HAVING COUNT(*) >= 10
),
ikkunat AS (
    -- 2. Liitetään tunnit toisiinsa muodostaen kolmen tunnin (eli yli 2h) seurantaikkunoita
    -- Joissa suurimman ja pienimmän eron spread on alle 5 metriä (500cm).
    SELECT 
        a.node_id, 
        a.paiva, 
        a.tunti AS tunti_alku,
        MAX(SQRT(POWER(b.med_x-a.med_x,2)+POWER(b.med_y-a.med_y,2))) AS spread_cm,
        AVG(b.med_x) AS keski_x,
        AVG(b.med_y) AS keski_y
    FROM per_tunti a
    JOIN per_tunti b ON a.node_id = b.node_id AND a.paiva = b.paiva
        AND b.tunti >= a.tunti AND b.tunti <= a.tunti + INTERVAL 2 HOUR
    GROUP BY a.node_id, a.paiva, a.tunti
    HAVING COUNT(DISTINCT b.tunti) >= 3
       AND MAX(SQRT(POWER(b.med_x-a.med_x,2)+POWER(b.med_y-a.med_y,2))) < 500
),
uniikki AS (
    -- 3. Järjestetään kaikki tällaiset tunnistetut paikallaanolot ja merkitään
    -- edellisen tunnistuksen alkuaika jotta saamme parsittua erilliset sessionkatkot
    SELECT 
        *,
        LAG(tunti_alku) OVER (PARTITION BY node_id, paiva ORDER BY tunti_alku) AS prev_t
    FROM ikkunat
)

-- 4. Lopullinen siivous ja muotoilu analytiikkaa varten
SELECT
    node_id,
    paiva,
    tunti_alku,
    ROUND(keski_x, 0) AS x,
    ROUND(keski_y, 0) AS y,
    ROUND(spread_cm, 0) AS spread_cm
FROM uniikki
-- Suodatetaan päällekkäisyydet: joko ensimmäinen instanssi tai ainakin 2 tuntia taukoa edellisestä listauksesta
WHERE prev_t IS NULL OR tunti_alku > prev_t + INTERVAL 2 HOUR
ORDER BY paiva, tunti_alku
