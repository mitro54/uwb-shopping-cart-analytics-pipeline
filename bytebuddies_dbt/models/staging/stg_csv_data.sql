{{ config(materialized='table') }}

SELECT
    node_id::INT as node_id,
    timestamp::TIMESTAMPTZ as timestamp,
    x::INT as x,
    y::INT as y,
    z::INT as z,
    q::INT as q,
    filename
FROM read_csv_auto('../data/raw/*.csv', filename=true)
