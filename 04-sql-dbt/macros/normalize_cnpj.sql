{% macro normalize_cnpj(col) %}
COALESCE(
    REGEXP_REPLACE(
        REGEXP_REPLACE(
            COALESCE(CAST({{ col }} AS VARCHAR), ''),
            '[^0-9]', '', 'g'
        ),
        '^0+', ''
    ),
    ''
)
{% endmacro %}
