{{ config(
    materialized='table',
    post_hook=[
        "CREATE UNIQUE INDEX IF NOT EXISTS pk_dim_karry ON {{ this }} (node_id)"
    ]
) }}

-- Kärry-dimensio: Yhdistää uniikit kärryt ja niiden elinkaaren
SELECT
    node_id,
    'Kärry ' || node_id AS snro, -- Generoitu sarjanumero
    MIN(aika) AS luotu,
    MAX(aika) AS viim_havainto
FROM {{ ref('silver_positions') }}
GROUP BY node_id
