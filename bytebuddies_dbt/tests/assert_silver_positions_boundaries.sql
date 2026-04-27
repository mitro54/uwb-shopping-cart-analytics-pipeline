-- Tuotannon data-laadun varmistaminen (Singular Test)
-- dbt olettaa, että testit menevät läpi JOS tämä kysely ei löydä yhtään riviä!
-- Haetaan siis tietokannan rivit, jotka RIKKOVAT sovittuja sääntöjä:

SELECT *
FROM {{ ref('silver_positions') }}
WHERE 
    q <= {{ var('q_threshold') }}
    OR EXTRACT('hour' FROM aika) < {{ var('shop_open') }}
    OR EXTRACT('hour' FROM aika) > {{ var('shop_close') }}
    OR EXTRACT('isodow' FROM aika) < 1
    OR EXTRACT('isodow' FROM aika) > 7
    OR speed_mps > {{ var('max_jump_speed') }} + 0.1
