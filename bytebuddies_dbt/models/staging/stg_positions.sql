{{ config(materialized='view') }}

WITH puhdistettu AS (
    -- 1. Silver-tason peruspuhdistus
    SELECT DISTINCT
        node_id,
        timestamp AS aika,
        x,
        y,
        q
    FROM {{ ref('stg_csv_data') }}
    WHERE 
        q > 0 
        AND x IS NOT NULL 
        AND y IS NOT NULL
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
    FROM puhdistettu
),
rikastettu AS (
    -- 3. Lasketaan matka, aikaväli ja nopeus
    SELECT
        *,
        -- Matka (Pythagoraan lause)
        SQRT(POWER(x - edellinen_x, 2) + POWER(y - edellinen_y, 2)) AS matka_edellisesta,
        -- Aikaväli sekunteina
        DATE_DIFF('second', edellinen_aika, aika) AS sekuntia_edellisesta
    FROM liikkeet
)
SELECT
    *,
    -- Nopeus (yksikköä / sekunti), vältetään nollalla jakaminen
    CASE 
        WHEN sekuntia_edellisesta > 0 THEN matka_edellisesta / sekuntia_edellisesta 
        ELSE 0 
    END AS nopeus
FROM rikastettu