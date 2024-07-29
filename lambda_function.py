"""
The Slack Lambda Button module for the Duderstadt Center
"""

import json
import sys
import time

from typing import List

from datetime import datetime
from subprocess import DEVNULL, STDOUT, check_call
import requests

import boto3
import sheets

is_raspberry_pi = not sys.platform.startswith("win32")

# Read the configuration files
try:
    with open('config.json', 'r', encoding="utf8") as file:
        CONFIG = json.load(file)
except json.JSONDecodeError as e:
    print(e)
except FileNotFoundError as e:
    with open("config.json", "x", encoding="utf8") as file:
        print("config.json not found, creating it for you...")

        defaults = {"webhook_url": "", "button_config": {"device_id": ""}}
        json.dump(defaults, file)
try:
    with open("aws.json", "r", encoding="utf8") as file:
        AWS = json.load(file)
except json.JSONDecodeError as e:
    print(e)
except FileNotFoundError as e:
    with open("aws.json", "x", encoding="utf8") as file:
        print("aws.json not found, creating it for you...")

        defaults = {"AWS_ACCESS_KEY_ID": "", "AWS_SECRET_ACCESS_KEY": ""}
        json.dump(defaults, file)
    exit()

WEBHOOK_URL = CONFIG["webhook_url"]
BUTTON_CONFIG = CONFIG["button_config"]

# Dictionary to store the timestamp of the last message sent for each button
LAST_MESSAGE_TIMESTAMP = {}

def init_aws() -> boto3.client:
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

    Params:
    sheets_service -> the Google Sheets service we're working with
    spreadsheet_id -> the id of the spreadsheet we're working on
    device_id -> the id of this specific device, received from config.json
    """

    last_row = sheets.find_first_empty_row(sheets_service, spreadsheet_id)

    device_id_list = sheets.get_region(sheets_service, spreadsheet_id,
                            first_row = 2, last_row = last_row,
                            first_letter = "B", last_letter = "B")

    device_id_list = [id[0].strip() if id != [] else "" for id in device_id_list]
    try:
        device_index = device_id_list.index(device_id) + 2 # add 2 because skip first row + Google Sheets is 1 indexed
    except ValueError:
        print(f"Unable to get device config. Device {device_id} was not listed. Exiting.")
        sys.exit()

    device_info = sheets.get_region(sheets_service, spreadsheet_id,
                                    first_row = device_index, last_row = device_index,
                                    first_letter = "A", last_letter = "G")[0]

    return device_info

def post_to_slack(message, webhook_url):
    """
    Posts a message to Slack

    Params:
    message -> the message to send
    webhook_url -> the Slack webhook to use (per-channel?)
    """

    payload = {'text': message}
    response = requests.post(webhook_url, json=payload, timeout=10) # 10 second timeout
    return response.text

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
        response = requests.get("http://worldtimeapi.org/api/timezone/America/Detroit.json",
                                timeout=5)
        response_data = response.json()
        iso_datetime = response_data["datetime"]
        current_time = datetime.fromisoformat(iso_datetime)
        formatted_time = current_time.strftime("%B %d, %Y %I:%M:%S %p")

        # May be useful for keeping system time up-to-date throughout runtime
        if update_system_time and is_raspberry_pi:
            date_command = f"sudo date -s {iso_datetime}"
            date_command = date_command.split()
            check_call(date_command, stdout=DEVNULL, stderr=STDOUT)
    except requests.exceptions.Timeout:
        # Fall back on system time, though potentially iffy
        now = datetime.now()
        formatted_time = now.strftime("%B %d, %Y %I:%M:%S %p")

    return formatted_time

def handle_lambda(device_config: List[str], press_type: str = "SINGLE",
                  do_post: bool = True) -> dict:
    """
    Handle the Slack Lambda function

    Params:
    device_config: List[str] -> the device configuration information
    press_type: str = "SINGLE" -> the press type that we received (SINGLE or LONG)
    do_post: bool = True -> whether to post the message to Slack
    """

    device_id = device_config[1]
    # device_mac = device_config[2]
    device_location = device_config[3]
    # device_function = device_config[5]
    device_message = device_config[4]
    # device_alt_webhook = None

    # get the time but nice looking
    fancy_time = get_datetime(True)

    # handle timestamp, check for rate limit
    last_timestamp = LAST_MESSAGE_TIMESTAMP.get(device_id, 0)
    current_timestamp = time.time()
    if current_timestamp - last_timestamp < 60:
        print('Rate limit applied. Message not sent.')
        return {'statusCode': 429, 'body': 'Rate limit applied.'}

    # handle empty message/location
    final_message = device_message if device_message is not None and device_message != "" else "Unknown button pressed."
    final_location = device_location if device_location is not None and device_location != "" else "Unknown Location"

    # handle long button presses by sending a test message
    if press_type == "LONG":
        final_message = f"Testing button at {final_location}\nDevice ID: {device_id}\nTimestamp: {fancy_time}"

    print(f"\nINFO\n--------\nRetrieved message: {final_message}")
    print(f"Using Webhook: {WEBHOOK_URL}")

    # sort of mocking, I guess? I circumvent API calls, but it's not REALLY mocking is it?
    if do_post:
        slack_response = post_to_slack(final_message, WEBHOOK_URL)
        print(f"Received response from Slack: {slack_response}")

        LAST_MESSAGE_TIMESTAMP[device_id] = current_timestamp
    else:
        slack_response = "ok"
        print(f"\nMESSAGE\n--------\n{final_message}")

    return {'statusCode': 200, 'body': slack_response}

def handle_interaction(do_post: bool = True, press_length: int = 0) -> None:
    """
    Handles a button press or screen tap, basically just does the main functionality

    Params:
    do_post: bool = True -> whether to post to the Slack or just log in console, for debug
    press_length: int = 0 -> how long was the button pressed?
    """

    # aws_client = init_aws()

    press_type = "LONG" if press_length > 200 else "SINGLE"

    # set up Google Sheets and grab the config
    _, sheets_service, _, _, spreadsheet_id = sheets.setup_sheets()
    device_id = BUTTON_CONFIG["device_id"]

    device_config = get_config(sheets_service, spreadsheet_id, device_id)

    # send a message to Slack or the console
    handle_lambda(device_config, press_type=press_type, do_post=do_post)

if __name__ == "__main__":
    # testing
    handle_interaction(False, press_length = 634)
