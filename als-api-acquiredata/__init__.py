import json
import logging
import requests
import azure.functions as func

from shared_code.als_client import (
    get_als_samples,
    get_als_token,
    get_date_range_days,
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("als-api-acquiredata entered")

    try:
        start_date, end_date = get_date_range_days(7)

        token = get_als_token()

        samples = get_als_samples(
            token=token,
            start_date=start_date,
            end_date=end_date,
            only_completed_samples=True,
        )

        return func.HttpResponse(
            json.dumps(samples),
            mimetype="application/json",
            status_code=200,
        )

    except requests.exceptions.HTTPError as e:
        response = e.response

        logging.error(
            "ALS API HTTP error: status=%s url=%s body=%s",
            response.status_code if response else "unknown",
            response.url if response else "unknown",
            response.text[:1000] if response else "unknown",
        )

        return func.HttpResponse(
            json.dumps({
                "error": "ALS API returned an error.",
                "upstream_status": response.status_code if response else None,
                "upstream_body": response.text[:1000] if response else None,
            }),
            mimetype="application/json",
            status_code=502,
        )

    except Exception:
        logging.exception("Unhandled exception in als-api-acquiredata")

        return func.HttpResponse(
            json.dumps({"error": "Internal function error."}),
            mimetype="application/json",
            status_code=500,
        )