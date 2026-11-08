import json
import logging
import os
from datetime import datetime, timedelta
import azure.functions as func
import requests

from shared_code.als_client import get_als_token, get_als_samples
from shared_code.als_transform import transform_als_payload
from shared_code.sql_writer import build_sql_statements


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Fetching and transforming ALS lab data.")

    try:
        project_no = req.params.get("sample_type_name")
        workorder_code = req.params.get("batch_no")
        from_days_ago = int(req.params.get("from_days_ago", 50))

        token = get_als_token()

        start_date, end_date = get_date_range(from_days_ago)

        als_payload = get_als_samples(
            token=token,
            start_date=start_date,
            end_date=end_date,
        )

        prepared_rows = transform_als_payload(
            payload=als_payload,
            sample_type_name=project_no,
        )

        sql_statements = build_sql_statements(prepared_rows)

        if not sql_statements:
            return func.HttpResponse(
                body="-- No matching ALS samples or mapped analytes found.\n",
                mimetype="application/sql",
                status_code=200,
            )

        sql_content = "\n".join(sql_statements)
        filename = (
            f"lab_data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql"
        )

        return func.HttpResponse(
            body=sql_content,
            mimetype="application/sql",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )

    except Exception:
        logging.exception("Unhandled exception in als-api-acquiredata")

        return func.HttpResponse(
            json.dumps({"error": "Internal function error."}),
            mimetype="application/json",
            status_code=500,
        )


def get_date_range(days: int) -> tuple[str, str]:
    end_utc = datetime.utcnow()
    start_utc = end_utc - timedelta(days=days)

    return (
        start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )