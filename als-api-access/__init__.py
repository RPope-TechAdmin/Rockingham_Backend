# File: /HttpTriggerAPI/__init__.py
import os
import json
import logging
import requests
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Authenticating with ALS API...")

    try:
        api_url = "https://gip.alsglobal.com/api/Login"

        api_key = os.environ["API_KEY"]
        service_key = os.environ["API_SERVICEKEY"]

        headers = {
            "Accept": "*/*",
            "X-Service-Key": service_key,
        }

        body = {
            "key": api_key,
        }

        response = requests.post(
            api_url,
            headers=headers,
            json=body,
            timeout=10,
        )

        if response.status_code == 401:
            logging.error("Unauthorized: check service key, API key, or environment.")
            return func.HttpResponse(
                json.dumps({
                    "error": "Unauthorized. Verify service key, API key, or API URL.",
                    "details": response.text,
                }),
                mimetype="application/json",
                status_code=401,
            )

        response.raise_for_status()

        token = response.json()

        return func.HttpResponse(
            json.dumps({"status": "success", "response": token}),
            mimetype="application/json",
            status_code=200,
        )

    except requests.exceptions.Timeout:
        logging.error("ALS API request timed out.")
        return func.HttpResponse(
            json.dumps({"error": "ALS API request timed out."}),
            mimetype="application/json",
            status_code=504,
        )

    except requests.exceptions.HTTPError as e:
            logging.error(
                "ALS API HTTP error: status=%s response=%s",
                response.status_code,
                response.text[:1000],
            )
            return func.HttpResponse(
                json.dumps({
                    "error": "ALS API returned an error.",
                    "upstream_status": response.status_code,
                    "upstream_body": response.text[:1000],
                }),
                mimetype="application/json",
                status_code=502,
            )

    except requests.exceptions.RequestException as e:
        logging.error(f"ALS API request failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=502,
        )

    except Exception:
        logging.exception("Unhandled exception in als-api-access")
        return func.HttpResponse(
            json.dumps({
                "error": "Internal function error. See Function App logs."
            }),
            mimetype="application/json",
            status_code=500,
        )