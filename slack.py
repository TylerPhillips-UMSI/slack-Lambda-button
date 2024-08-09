#!/usr/bin/env python3

"""
The Slack Lambda Button module for the Duderstadt Center

Author:
Nikki Hess (nkhess@umich.edu)
"""

import json
import sys
import time

from typing import List

from datetime import datetime
from subprocess import DEVNULL, STDOUT, check_call
import requests

import sheets

is_raspberry_pi = not sys.platform.startswith("win32")

# Read the configuration files
try:
    with open("slack.json", "r", encoding="utf8") as file:
        CONFIG = json.load(file)
except json.JSONDecodeError as e:
    print(e)
except FileNotFoundError as e:
    with open("slack.json", "x", encoding="utf8") as file:
        print("slack.json not found, creating it for you...")

        defaults = {"bot_oauth_token": "", "button_config": {"device_id": ""}}
        json.dump(defaults, file)

BUTTON_CONFIG = CONFIG["button_config"]
BOT_OAUTH_TOKEN = CONFIG["bot_oauth_token"]

# Dictionary to store the timestamp of the last message sent for each button
LAST_MESSAGE_TIMESTAMP = {}

def get_config(sheets_service, spreadsheet_id: int, device_id: str) -> List[str]:
    """
    Gets the configuration for a button from Google Sheets
    and returns it as a List

    Args:
        sheets_service: the Google Sheets service we're working with
        spreadsheet_id (int): the id of the spreadsheet we're working on
        device_id (str): the id of this specific device, received from slack.json
    """

    last_row = sheets.find_first_empty_row(sheets_service, spreadsheet_id)

    device_id_list = sheets.get_region(sheets_service, spreadsheet_id,
                                        first_row = 2, last_row = last_row,
                                        first_letter = "B", last_letter = "B")

    device_id_list = [id[0].strip() if id != [] else "" for id in device_id_list]
    try:
        # add 2 because skip first row + Google Sheets is 1 indexed
        device_index = device_id_list.index(device_id) + 2
    except ValueError:
        print(f"Unable to get device config. Device {device_id} was not listed. Exiting.")
        sys.exit()

    try:
        device_info = sheets.get_region(sheets_service, spreadsheet_id,
                                        first_row = device_index, last_row = device_index,
                                        first_letter = "A", last_letter = "I")[0]
    except IndexError:
        print("Index out of range when selecting device config. Did you forget to set the device ID (slack.json)?")
        sys.exit()

    return device_info

def get_datetime(update_system_time: bool = False) -> str | None:
    """
    Gets the current datetime as a beautifully formatted string

    Args:
        update_system_time (bool): whether to update the system time (Linux only)

    Returns:
        formatted_time (str | None): the formatted time string, if present
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

    Args:
        device_config (list): the device configuration information
        press_type (str): the press type that we received (SINGLE or LONG)
        do_post (bool): whether to post the message to Slack
    """

    device_id = device_config[1]
    # device_mac = device_config[2]
    device_location = device_config[3]
    # device_function = device_config[5]
    device_message = device_config[4]
    # device_alt_webhook = None
    device_rate_limit = int(device_config[7])
    device_channel_id = device_config[8]

    # get the time but nice looking
    fancy_time = get_datetime(True)

    # handle timestamp, check for rate limit
    last_timestamp = LAST_MESSAGE_TIMESTAMP.get(device_id, 0)
    current_timestamp = time.time()

    if current_timestamp - last_timestamp < device_rate_limit:
        print("Rate limit applied. Message not sent.")
        return {"statusCode": 429, "body": "Rate limit applied."}

    # handle empty message/location
    if device_message is None or device_message == "":
        final_message = "Unknown button pressed."
    else:
        final_message = device_message

    # Check and assign device_location
    if device_location is None or device_location == "":
        final_location = "Unknown Location"
    else:
        final_location = device_location

    # handle long button presses by sending a test message
    if press_type == "LONG":
        final_message = f"Testing button at {final_location}"
        final_message += f"\nDevice ID: {device_id}\nTimestamp: {fancy_time}"

    print(f"\nINFO\n--------\nRetrieved message: {final_message}")

    # sort of mocking, I guess? I circumvent API calls, but it's not REALLY mocking is it?
    if do_post:
        slack_response = post_to_slack(message=final_message, channel_id=device_channel_id)
        print(f"Received response from Slack: {slack_response}")

        LAST_MESSAGE_TIMESTAMP[device_id] = current_timestamp
    else:
        slack_response = "ok"
        print(f"\nMESSAGE\n--------\n{final_message}")

    return {"statusCode": 200, "body": slack_response}

def handle_interaction(do_post: bool = True, press_length: float = 0) -> None:
    """
    Handles a button press or screen tap, basically just does the main functionality

    Args:
        do_post (bool): whether to post to the Slack or just log in console, for debug
        press_length (float): how long was the button pressed?
    """

    press_type = "LONG" if press_length > 2 else "SINGLE"

    # set up Google Sheets and grab the config
    _, sheets_service, _, _, spreadsheet_id = sheets.setup_sheets()
    device_id = BUTTON_CONFIG["device_id"]

    device_config = get_config(sheets_service, spreadsheet_id, device_id)

    # send a message to Slack or the console
    handle_lambda(device_config, press_type=press_type, do_post=do_post)

if __name__ == "__main__":
    # testing
    handle_interaction(do_post = True, press_length = 634)
