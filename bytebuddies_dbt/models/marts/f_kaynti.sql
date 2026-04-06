{{ config(materialized='table') }}

-- Yhdistetään ja aggregoidaan koko käynnin tiedot yhteen riviin per kärry.
-- Matka on jo valmiiksi laskettuna Silver-tason stg_positions-näkymässä!
SELECT
    MD5(node_id || 'kaynti') AS kaynti_id, -- Generoidaan uniikki ID käynnille
    node_id,
    MIN(aika) AS alku,
    MAX(aika) AS loppu,
    DATE_DIFF('second', MIN(aika), MAX(aika)) AS kesto_sekunteina,
    COALESCE(SUM(matka_edellisesta), 0) AS matka
FROM {{ ref('stg_positions') }}
GROUP BY node_id