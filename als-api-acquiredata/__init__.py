import json
import logging
import os
from datetime import datetime, timezone, timedelta
import azure.functions as func
import requests


ALS_BASE_URL = "https://gip.alsglobal.com"
LOGIN_URL = f"{ALS_BASE_URL}/Login"
SAMPLES_URL = f"{ALS_BASE_URL}/WebTrieve/Results/Data"


def get_als_token() -> str:
    api_key = os.environ["API_KEY"]
    service_key = os.environ["API_SERVICEKEY"]

    response = requests.post(
        LOGIN_URL,
        headers={
            "Content-Type": "application/json",
            "Accept": "*/*",
            "X-Service-Key": service_key,
        },
        json={"key": api_key},
        timeout=(5, 30),
    )
    response.raise_for_status()

    payload = response.json()

    # Adjust this field name once you confirm the login response structure.
    token = (
        payload.get("token")
        or payload.get("Token")
        or payload.get("accessToken")
        or payload.get("access_token")
    )

    if not token:
        raise ValueError("ALS login response did not contain an expected token field.")

    return token


def get_als_samples(
    token: str,
    start_utc: datetime,
    end_utc: datetime,
    only_completed_samples: bool = True,
    language_code: str = "en-GB",
) -> dict:
    service_key = os.environ["API_SERVICEKEY"]

    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "X-Service-Key": service_key,
        "Authorization": f"Bearer {token}",
    }

    params = {
        "EndDateTimeUTC": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "StartDateTimeUTC": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "OnlyCompletedSamples": str(only_completed_samples).lower(),
        "LanguageCode": language_code,
    }

    response = requests.get(
        SAMPLES_URL,
        headers=headers,
        params=params,
        timeout=(5, 60),
    )

    logging.info(
        "ALS data response: status=%s url=%s content_type=%s",
        response.status_code,
        response.url,
        response.headers.get("Content-Type"),
    )

    response.raise_for_status()

    if response.status_code == 204 or not response.text.strip():
        logging.info("ALS returned no data for the requested period.")
        return {
            "data": [],
            "message": "No results found for the requested date range and filters.",
        }

    return response.json()


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("als-api-access entered")

    try:
        end_utc = datetime.now(datetime.timezone.utc)
        start_utc = datetime.now(datetime.timezone.utc) - timedelta(days=7)

        token = get_als_token()
        samples = get_als_samples(
            token=token,
            start_utc=start_utc,
            end_utc=end_utc,
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
            "ALS API HTTP error: status=%s url=%s response=%s",
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
        logging.exception("Unhandled exception in als-api-access")

        return func.HttpResponse(
            json.dumps({"error": "Internal function error."}),
            mimetype="application/json",
            status_code=500,
        )