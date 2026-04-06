{{ config(materialized='view') }}

-- Silver-tason puhdistettu data (Medallion-arkkitehtuuri)
SELECT DISTINCT
    node_id,
    timestamp AS aika,
    x,
    y,
    q
FROM {{ ref('stg_csv_data') }}
WHERE 
    -- Suodatetaan pois heikkolaatuiset ja virheelliset mittaukset (q-arvo)
    q > 0 
    AND x IS NOT NULL 
    AND y IS NOT NULL