{{ config(materialized='table') }}

-- =========================================================================
-- 🥇 GOLD: gold_reitit — Yksittäiseen reittiin liittyvät filtteröinnit
-- =========================================================================
-- Lähde  : silver_positions
-- Tavoite: Vain validit sessiot (oikeat kauppareissut), jotka alkavat 
-- sisäänkäynniltä ja päättyvät kassoille, ja täyttävät asioinnin minimivaatimukset.
-- =========================================================================

-- Validointi ja filtteröinti tehdään nykyään jo silver_positions -tasolla
-- Tämän tason ainoa tarkoitus on poistaa kassa-alueen pisteet visualisointia varten,
-- jotta kärryjen reitit näyttävät siisteiltä kartalla (kassoille ei tule sumppua).

SELECT * EXCLUDE(in_checkout)
FROM {{ ref('silver_positions') }}
WHERE in_checkout = 0
