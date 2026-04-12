-- Osastodimensio: Tuotu tuotantoon staattisesta dbt seed -taulusta.
-- Näin osastot ovat oikeaoppisesti Gold-kerroksen dimensioita, joihin voidaan hakea myöhemmin dataa myös muualta.
SELECT
    osasto_id,
    nimi,
    alku_x,
    alku_y,
    loppu_x,
    loppu_y
FROM {{ ref('osastot') }}
