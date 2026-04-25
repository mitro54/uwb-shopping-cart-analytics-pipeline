{% macro get_exclusion_zones() %}
    {% set ext_zones_str = env_var('EXCLUDED_ZONES_JSON', '[]') %}
    {% set zones = fromjson(ext_zones_str) %}
    {% set sql = [] %}

    {% for zone in zones %}
        {% set conditions = [] %}
        {% if 'x_min' in zone %}{% do conditions.append("(x/100.0) >= " ~ zone.x_min) %}{% endif %}
        {% if 'x_max' in zone %}{% do conditions.append("(x/100.0) <= " ~ zone.x_max) %}{% endif %}
        {% if 'y_min' in zone %}{% do conditions.append("(y/100.0) >= " ~ zone.y_min) %}{% endif %}
        {% if 'y_max' in zone %}{% do conditions.append("(y/100.0) <= " ~ zone.y_max) %}{% endif %}
        
        {% if conditions | length > 0 %}
            {% do sql.append("AND NOT (" ~ conditions | join(' AND ') ~ ")") %}
        {% endif %}
    {% endfor %}

    {{ return(sql | join('\n        ')) }}
{% endmacro %}
