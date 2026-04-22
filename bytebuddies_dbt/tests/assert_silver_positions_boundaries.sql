-- Tuotannon data-laadun varmistaminen (Singular Test)
-- dbt olettaa, että testit menevät läpi JOS tämä kysely ei löydä yhtään riviä!
-- Haetaan siis tietokannan rivit, jotka RIKKOVAT sovittuja sääntöjä:

SELECT *
FROM {{ ref('silver_positions') }}
WHERE 
    q <= {{ var('q_threshold') }}
    OR hour < {{ var('shop_open') }}
    OR hour > {{ var('shop_close') }}
    OR weekday < 1
    OR weekday > 7
    OR speed_mps > {{ var('max_jump_speed') }} + 0.1
