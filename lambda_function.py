"""
The Slack Lambda Button module for the Duderstadt Center
"""

import json
import time

import requests
from datetime import datetime
from subprocess import DEVNULL, STDOUT, check_call

import boto3
import sheets

from typing import List

# Read the configuration file
try:
    with open('config.json', 'r', encoding="utf8") as file:
        CONFIG = json.load(file)
    with open("aws.json", "r", encoding="utf8") as file:
        AWS = json.load(file)
except json.JSONDecodeError as e:
    with open('config.json', 'r', encoding="utf8") as file:
        print(f"Error decoding JSON: {e}")
        file_content = file.read()
        lines = file_content.split('\n')
        if 0 <= e.lineno < len(lines):
            print(f"Problematic line: {lines[e.lineno]}")
    raise

WEBHOOK_URL = CONFIG["webhook_url"]
BUTTON_CONFIG = CONFIG["button_config"]

# Dictionary to store the timestamp of the last message sent for each button
LAST_MESSAGE_TIMESTAMP = {}

def init_aws():
    """
    Initializes boto3/AWS
    """

    client = boto3.client('iot-data', 
                          aws_access_key_id=AWS["AWS_ACCESS_KEY_ID"],
                          aws_secret_access_key=AWS['AWS_SECRET_ACCESS_KEY'], region_name="Ohio")

    return client

def get_config(sheets_service, spreadsheet_id: int, device_id: str) -> List[str]:
    """
    Gets the configuration for a button from Google Sheets
    and returns it as a List
    """

    last_row = sheets.find_first_empty_row(sheets_service, spreadsheet_id)

    device_id_list = sheets.get_region(sheets_service, spreadsheet_id,
                            first_row = 2, last_row = last_row,
                            first_letter = "B", last_letter = "B")

    device_id_list = [id[0].strip() if id != [] else "" for id in device_id_list]
    device_index = device_id_list.index(device_id) + 2 # add 2 because skipped first row + Google Sheets is 1 indexed

    device_info = sheets.get_region(sheets_service, spreadsheet_id,
                                    first_row = device_index, last_row = device_index,
                                    first_letter = "A", last_letter = "G")[0]

    return device_info

def post_to_slack(message, webhook_url):
    """
    Posts a message to Slack
    """
    
    payload = {'text': message}
    response = requests.post(webhook_url, json=payload)
    return response.text


def lambda_handler(event, context):
    print(event)
    device_info = event.get('deviceInfo', {})
    device_id = device_info.get('deviceId', '').strip()
    click_type = event['deviceEvent']['buttonClicked']['clickType']
    remaining_life = device_info.get('remainingLife', '')
    reported_time = event['deviceEvent']['buttonClicked']['reportedTime']

    print(f"Extracted deviceId: {device_id}, clickType: {click_type}")

    if not device_id:
        print('No deviceId provided.')
        return {'statusCode': 400, 'body': 'No deviceId provided.'}

    last_timestamp = LAST_MESSAGE_TIMESTAMP.get(device_id, 0)
    current_timestamp = time.time()
    if current_timestamp - last_timestamp < 60:
        print('Rate limit applied. Message not sent.')
        return {'statusCode': 429, 'body': 'Rate limit applied.'}

    button_details = BUTTON_CONFIG.get(device_id, {})
    message = button_details.get(click_type, f"Unknown button pressed.")
    location = button_details.get("LOCATION", "Default Location")

    if click_type == "LONG":
        message = f"Testing button {location} {device_id} battery life is {remaining_life} at {reported_time}"

    webhook_url = button_details.get("WEBHOOK_URL") or WEBHOOK_URL

    print(f"Retrieved message: {message}")
    print(f"Using Webhook: {webhook_url}")

    slack_response = post_to_slack(message, webhook_url)
    print(f"Received response from Slack: {slack_response}")

    LAST_MESSAGE_TIMESTAMP[device_id] = current_timestamp

    return {'statusCode': 200, 'body': slack_response}

def get_datetime(update_system_time: bool = False) -> str | None:
    """
    Gets the current datetime as a beautifully formatted string

    Params:
    update_system_time: bool -> whether to update the system time (Linux only)

    Returns:
    formatted_time: str | None -> the formatted time string, if present
    """

    formatted_time = None
    try:
        response = requests.get("http://worldtimeapi.org/api/timezone/America/Detroit.json", timeout=5)
        response_data = response.json()
        iso_datetime = response_data["datetime"]
        current_time = datetime.fromisoformat(iso_datetime)
        formatted_time = current_time.strftime("%B %d, %Y %I:%M:%S %p")

        # May be useful for keeping system time up-to-date throughout runtime
        if update_system_time:
            date_command = f"sudo date -s {iso_datetime}"
            date_command = date_command.split()
            check_call(date_command, stdout=DEVNULL, stderr=STDOUT)
    except requests.exceptions.Timeout:
        # Fall back on system time, though potentially iffy
        now = datetime.now()
        formatted_time = now.strftime("%B %d, %Y %I:%M:%S %p")
    finally:
        return formatted_time

def handle_lambda(device_config: List[str], press_type: str = "SINGLE", actually_post: bool = True):
    device_mac = device_config[2]
    device_location = device_config[3]
    device_function = device_config[5]
    device_message = device_config[4]
    device_alt_webhook = None

    # handle timestamp, check for rate limit
    last_timestamp = LAST_MESSAGE_TIMESTAMP.get(device_id, 0)
    current_timestamp = time.time()
    if current_timestamp - last_timestamp < 60:
        print('Rate limit applied. Message not sent.')
        return {'statusCode': 429, 'body': 'Rate limit applied.'}


    final_message = press_type if press_type is not None and press_type != "" else "Unknown button pressed."
    final_location = device_location if device_location is not None and device_location != "" else "Unknown Location"

    if press_type == "LONG":
        final_message = f"Testing button at {final_location}\nDevice ID: {device_id}\nTimestamp: {get_datetime(True)}"

    print(f"Retrieved message: {final_message}")
    print(f"Using Webhook: {WEBHOOK_URL}")

    slack_response = post_to_slack(final_message, WEBHOOK_URL)
    print(f"Received response from Slack: {slack_response}")

    LAST_MESSAGE_TIMESTAMP[device_id] = current_timestamp

    return {'statusCode': 200, 'body': slack_response}
    

if __name__ == "__main__":
    aws_client = init_aws()

    _, sheets_service, _, _, spreadsheet_id = sheets.setup_sheets()
    device_id = BUTTON_CONFIG["device_id"]

    device_config = get_config(sheets_service, spreadsheet_id, device_id)

    handle_lambda(device_config, click_type="LONG")
