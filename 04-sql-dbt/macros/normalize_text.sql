{% macro normalize_text(col) %}
TRIM(
    REGEXP_REPLACE(
        REGEXP_REPLACE(
            STRIP_ACCENTS(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(
                                REPLACE(
                                    REPLACE(
                                        UPPER(TRIM(COALESCE(CAST({{ col }} AS VARCHAR), ''))),
                                        '- PRUDENCIAL', ''
                                    ),
                                    '(CONGLOMERADO)', ''
                                ),
                                'S.A.', ''
                            ),
                            'S/A', ''
                        ),
                        'LTDA', ''
                    ),
                    '-PRUDENCIAL', ''
                )
            ),
            '[^A-Z0-9 ]', '', 'g'
        ),
        '\\s+', ' ', 'g'
    )
)
{% endmacro %}
