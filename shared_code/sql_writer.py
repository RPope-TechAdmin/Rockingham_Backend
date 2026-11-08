from typing import Any

from shared_code.references import TABLE_FIELD_MAP_ROCKINGHAM


def sql_string(value: Any) -> str:
    if value is None:
        return "NULL"

    return "'" + str(value).replace("'", "''") + "'"


def sql_value(value: Any) -> str:
    if value is None:
        return "NULL"

    if isinstance(value, (int, float)):
        return str(value)

    return sql_string(value)


def build_insert_sql(row: dict[str, Any]) -> str | None:
    project_table = row.get("_project_table")

    if not project_table:
        return None

    fields = TABLE_FIELD_MAP_ROCKINGHAM.get(project_table)

    if not fields:
        return None

    values = []

    for field in fields:
        values.append(sql_value(row.get(field)))

    field_list = ", ".join(f"[{field}]" for field in fields)
    value_list = ", ".join(values)

    return (
        f"INSERT INTO [Rockingham].[{project_table}] "
        f"({field_list}) VALUES ({value_list});"
    )


def build_sql_statements(prepared_rows: list[dict[str, Any]]) -> list[str]:
    statements = []

    for row in prepared_rows:
        sql = build_insert_sql(row)

        if sql:
            statements.append(sql)

    return statements