import requests
import json
import urllib3

def get_all_agency_info():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute"

    params = {
        "cacheable": "true",
        "classname": "@udd/01p8z0000009E4V",
        "isContinuation": "false",
        "method": "getAgenciesDetail",
        "namespace": "",
        "params": json.dumps({"recordId": None}),
        "language": "en-US",
        "asGuest": "true",
        "htmlEncode": "false"
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    try:
        print("GET request with recordId=null")
        response = requests.get(base_url, params=params, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"GET request with recordId=null failed: {e}")
        return None

def get_agency_document_list(record_id):
    """
    POST with JSON payload directly to the API endpoint
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute"

    # JSON payload
    payload = {
        "namespace": "",
        "classname": "@udd/01p8z0000009E4V",
        "method": "getContentDetails",
        "isContinuation": False,
        "params": {
            "recordId": record_id
        },
        "cacheable": False
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://michildwelfarepubliclicensingsearch.michigan.gov',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    try:
        print("POST with JSON payload directly to the API endpoint")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(
            base_url,
            json=payload,
            headers=headers,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"POST with JSON payload directly to the API endpoint failed: {e}")
        if 'response' in locals():
            print(f"Response content: {response.text}")
        return None

