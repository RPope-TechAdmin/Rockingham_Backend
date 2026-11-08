import logging
import os
import requests
from datetime import datetime, timedelta, timezone
from __init__ import from_days_ago

logger = logging.getLogger(__name__)

ALS_BASE_URL = "https://gip.alsglobal.com"
LOGIN_URL = f"{ALS_BASE_URL}/Login"
SAMPLES_URL = f"{ALS_BASE_URL}/WebTrieve/Results/Data"


def get_date_range_days(days: int = from_days_ago) -> tuple[str, str]:
    end_utc = datetime.now(timezone.utc)
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
) -> dict:
    params = {
        "StartDateTimeUTC": start_date,
        "EndDateTimeUTC": end_date,
        "OnlyCompletedSamples": "true",
        "LanguageCode": "en-GB",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    logger.info(
        "ALS data request: method=%s url=%s params=%s",
        "GET",
        SAMPLES_URL,
        params,
    )

    try:
        response = requests.get(
            SAMPLES_URL,
            headers=headers,
            params=params,
            timeout=30,
        )

        logger.info(
            "ALS data response: status=%s elapsed_seconds=%.2f "
            "content_type=%s content_length=%s",
            response.status_code,
            response.elapsed.total_seconds(),
            response.headers.get("Content-Type"),
            response.headers.get("Content-Length"),
        )

        # Useful support-correlation headers, if ALS returns them.
        for header_name in (
            "X-Request-Id",
            "Request-Id",
            "Correlation-Id",
            "X-Correlation-ID",
        ):
            if response.headers.get(header_name):
                logger.info(
                    "ALS response header: %s=%s",
                    header_name,
                    response.headers[header_name],
                )

        if not response.ok:
            response_body = response.text[:2000]

            logger.error(
                "ALS data request failed: status=%s reason=%s "
                "url=%s response_body=%r",
                response.status_code,
                response.reason,
                response.url,
                response_body,
            )

            response.raise_for_status()

        return response.json()

    except requests.exceptions.Timeout:
        logger.error(
            "ALS data request timed out: url=%s start=%s end=%s",
            SAMPLES_URL,
            start_date,
            end_date,
        )
        raise

    except requests.exceptions.RequestException:
        logger.exception(
            "ALS data request failed: url=%s start=%s end=%s",
            SAMPLES_URL,
            start_date,
            end_date,
        )
        raise