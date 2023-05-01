# alert.py
import os
import requests

SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']

def send_slack_alert(message):
    payload = {'text': message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)

    if response.status_code != 200:
        raise ValueError(f"Request to slack returned an error {response.status_code}, the response is:\n{response.text}")

