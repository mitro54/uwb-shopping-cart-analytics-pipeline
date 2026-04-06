{{ config(materialized='table') }}

SELECT
    node_id::VARCHAR as node_id,
    timestamp::TIMESTAMPTZ as timestamp,
    x::INT as x,
    y::INT as y,
    q::INT as q,
    filename,
    CURRENT_TIMESTAMP AS latausajankohta
FROM read_csv_auto('../data/raw/*.csv', filename=true)
