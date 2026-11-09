import logging
import os
import requests
from datetime import datetime, timedelta, timezone


ALS_BASE_URL = "https://gip.alsglobal.com"
LOGIN_URL = f"{ALS_BASE_URL}/Login"
SAMPLES_URL = f"{ALS_BASE_URL}/WebTrieve/Results/Data"


def get_date_range_days(days: int = 7) -> tuple[str, str]:
    end_utc = datetime.now(timezone.utc) - timedelta(days=days)
    start_utc = end_utc - timedelta(days=days)

    return (
        start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


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
    token = payload.get("Token")

    if not token:
        raise ValueError("ALS login response did not contain a Token field.")

    return token


def get_als_samples(
    token: str,
    start_date: str,
    end_date: str,
    only_completed_samples: bool = True,
    language_code: str = "en-GB",
) -> dict:
    service_key = os.environ["API_SERVICEKEY"]

    headers = {
        "Accept": "*/*",
        "X-Service-Key": service_key,
        "Authorization": f"Bearer {token}",
    }

    params = {
        "StartDateTimeUTC": start_date,
        "EndDateTimeUTC": end_date,
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