-- =========================================================================
-- 🛒 PAIKALLAAN OLEVAT KÄRRYT (Yö- ja päivädata)
-- =========================================================================
-- Grain: Yksi rivi per paikallaanolojakso (>2h) per kärry.
-- Tarkoitus: Tunnistaa kauppaan hylätyt kärryt sekä yölatauksessa olevat 
-- laitteet hyödyntämällä liukuvaa ikkunaa 24/7 datasta (silver_device_diagnostics).
-- =========================================================================

WITH puhdistettu AS (
    SELECT 
        node_id,
        date_trunc('minute', aika) AS aika,
        MAX(is_night_time) AS is_night_time,
        AVG(x) AS x,
        AVG(y) AS y
    FROM {{ ref('silver_device_diagnostics') }}
    WHERE is_jitter = 0 AND is_out_of_bounds = 0
    GROUP BY 1, 2
),
windowed AS (
    SELECT
        *,
        -- 2 tunnin bounding box eteenpäin
        MAX(x) OVER w_2h - MIN(x) OVER w_2h AS spread_x,
        MAX(y) OVER w_2h - MIN(y) OVER w_2h AS spread_y,
        MAX(aika) OVER w_2h AS window_end_time
    FROM puhdistettu
    WINDOW w_2h AS (
        PARTITION BY node_id 
        ORDER BY aika 
        RANGE BETWEEN CURRENT ROW AND INTERVAL '2' HOUR FOLLOWING
    )
),
stationary_starts AS (
    SELECT
        *,
        -- Etsitään hetket jolloin ikkuna oikeasti kesti vähintään 2h ja kärry pysyi < 500cm säteellä
        CASE 
            WHEN DATE_DIFF('second', aika, window_end_time) >= 7200
             AND SQRT(POWER(spread_x, 2) + POWER(spread_y, 2)) < 500
            THEN 1 ELSE 0 
        END AS is_stationary_start
    FROM windowed
),
contiguous_blocks AS (
    SELECT
        *,
        -- Uusi jakso alkaa jos edellisestä paikallaanolon starttipingistä on yli 30 minuuttia.
        CASE 
            WHEN LAG(aika) OVER (PARTITION BY node_id ORDER BY aika) IS NULL 
              OR DATE_DIFF('minute', LAG(aika) OVER (PARTITION BY node_id ORDER BY aika), aika) > 30 
            THEN 1 ELSE 0 
        END AS new_block
    FROM stationary_starts
    WHERE is_stationary_start = 1
),
block_ids AS (
    SELECT
        *,
        SUM(new_block) OVER (PARTITION BY node_id ORDER BY aika) AS block_id
    FROM contiguous_blocks
),
aggregaatti AS (
    SELECT
        node_id,
        MIN(aika) AS alkuaika,
        -- Päättymisaika on viimeisen starttipisteen ikkunan loppu
        MAX(window_end_time) AS loppuaika,
        ROUND(AVG(x), 0) AS keski_x,
        ROUND(AVG(y), 0) AS keski_y,
        ROUND(MAX(SQRT(POWER(spread_x, 2) + POWER(spread_y, 2))), 0) AS max_spread_cm,
        CASE 
            WHEN MIN(is_night_time) = 1 THEN 'Yöaika'
            WHEN MAX(is_night_time) = 0 THEN 'Päiväaika'
            ELSE 'Yli yön (sekamuotoinen)'
        END AS aikaluokka,
        ROUND(DATE_DIFF('second', MIN(aika), MAX(window_end_time)) / 3600.0, 2) AS kesto_h,
        -- Merkitään latauspisteet configuroidun säteen mukaan
        CASE 
            WHEN (POWER(AVG(x) - {{ var('prob1_x') }}, 2) + POWER(AVG(y) - {{ var('prob1_y') }}, 2)) < POWER({{ var('prob1_r') }}, 2) THEN 1
            WHEN (POWER(AVG(x) - {{ var('prob2_x') }}, 2) + POWER(AVG(y) - {{ var('prob2_y') }}, 2)) < POWER({{ var('prob2_r') }}, 2) THEN 1
            ELSE 0
        END AS is_charging_station
    FROM block_ids
    GROUP BY node_id, block_id
)
SELECT 
    node_id,
    CAST(alkuaika AS DATE) AS paiva,
    alkuaika,
    loppuaika,
    kesto_h,
    keski_x AS x,
    keski_y AS y,
    max_spread_cm AS spread_cm,
    aikaluokka,
    is_charging_station
FROM aggregaatti
ORDER BY alkuaika, node_id
