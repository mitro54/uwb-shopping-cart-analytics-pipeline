-- Tuotannon data-laadun varmistaminen (Singular Test)
-- dbt olettaa, että testit menevät läpi JOS tämä kysely ei löydä yhtään riviä!
-- Haetaan siis tietokannan rivit, jotka RIKKOVAT sovittuja sääntöjä:

SELECT *
FROM {{ ref('silver_positions') }}
WHERE 
    q <= 35 
    OR hour < 7
    OR hour > 22
    OR weekday < 1
    OR weekday > 7
    OR speed_mps > 3.5
