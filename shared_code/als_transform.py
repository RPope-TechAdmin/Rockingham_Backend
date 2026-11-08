from datetime import datetime
from typing import Any
import logging
from shared_code.references import PROJECT_MAP, TABLE_FIELD_MAP


def normalise_identifier(value: str | None) -> str:
    return str(value or "").strip().lower()


def parse_als_date(value: str | None) -> str | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return value


def sanitise_result(value: str | None) -> str | None:
    if value is None:
        return None

    result = str(value).strip()
    lowered = result.lower()

    if any(symbol in lowered for symbol in ("<", "≤", ">", "≥", "~")):
        return None

    return result


def build_sample_row(
    batch: dict[str, Any],
    sample: dict[str, Any],
    tests: list[dict[str, Any]],
    project_table: str,
) -> dict[str, Any] | None:
    field_map = TABLE_FIELD_MAP.get(project_table)

    if not field_map:
        return None

    row = {field: None for field in field_map}

    row["File"] = batch.get("batchNo")
    row["Sample Location"] = sample.get("clientSiteName")
    row["Sample Name"] = sample.get("sampleNo")
    row["Sample Date"] = parse_als_date(sample.get("samplingDate"))

    for test in tests:
        analyte = test.get("testName")
        result = sanitise_result(test.get("resultText"))

        if analyte in field_map and result not in (None, ""):
            row[analyte] = result

    return row


def normalise_sample_type(value: str | None) -> str:
    return (value or "").strip().casefold()


def transform_als_payload(
    payload: dict[str, Any],
    sample_type_name: str | None = None,
) -> list[dict[str, Any]]:
    requested_type = normalise_sample_type(sample_type_name)

    table_routes = {
        normalise_sample_type(sample_type): table
        for sample_type, table in PROJECT_TABLE_ROUTES.items()
    }

    if requested_type and requested_type not in table_routes:
        raise ValueError(
            f"No SQL table mapped for sample type: {sample_type_name}"
        )

    prepared_rows = []

    for batch in payload.get("batches", []) or []:
        for sample in batch.get("samples", []) or []:
            actual_type = normalise_sample_type(
                sample.get("sampleTypeName")
            )

            # Apply the optional sample-type filter.
            if requested_type and actual_type != requested_type:
                continue

            project_table = table_routes.get(actual_type)

            if not project_table:
                logging.warning(
                    "Skipping sample %s: unmapped sampleTypeName=%r",
                    sample.get("sampleNo"),
                    sample.get("sampleTypeName"),
                )
                continue

            if not sample.get("sampleNo"):
                logging.warning("Skipping sample without sampleNo.")
                continue

            row = build_sample_row(
                batch=batch,
                sample=sample,
                tests=sample.get("tests", []) or [],
                project_table=project_table,
            )

            if row is not None:
                # Retain this key because the existing SQL writer uses it.
                row["_project_table"] = project_table
                prepared_rows.append(row)

    return prepared_rows