#!/usr/bin/env python3

"""
The AWS Lambda function code, not to be used locally.

Author:
Nikki Hess (nkhess@umich.edu)
"""

import json
import requests

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

pending_messages = []
message_to_channel = {} # pairs message ids with channel ids

def lambda_handler(event: dict, context: object):
    """
    AWS Lambda function entry point.

    Args:
        event (dict): the event data from Slack
        context (object): the runtime information

    Returns:
        dict: a response object for the HTTP request
    """
    # headers = event["headers"]
    body = event.get("body", {})

    slack_event = body.get("event", {})

    event_type = slack_event.get("type")

    if event_type == "message":
        handle_message(event)
    elif event_type == "reaction_added":
        handle_reaction_added(event)
    elif event_type == "post":
        channel_id = event["channel_id"]
        message = event["message"]
        post_to_slack(channel_id, message)

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "success"})
    }

def handle_message(event: dict) -> bool:
    """
    Handles messages for lambda_handler

    Args:
        event (dict): the event data from Slack

    Returns:
        resolved (bool): whether the message was marked as resolved, for GUI
    """
    message = event.get("text")
    thread_ts = event.get("ts")
    channel_id = message_to_channel.get(thread_ts)

    # going to be used in the GUI to determine if we should display the message
    resolved = False

    if thread_ts in pending_messages:
        if ":white_check_mark:" in message or ":+1:" in message:
            print(f"Message thread {thread_ts} has received a resolving response. Marking as resolved.")
            pending_messages.remove(thread_ts)

            mark_message_resolved(channel_id, thread_ts)

            resolved = True
    else:
        print("Timestamp was not in pending messages")

    return resolved

def handle_reaction_added(event: dict) -> bool:
    """
    Handles reactions for lambda_handler

    Args:
        event (dict): the event data from Slack

    Returns:
        resolved (bool): whether the message was marked as resolved, for GUI
    """
    reaction = event.get("reaction")
    item = event.get("item", {})
    ts = item.get("ts")
    channel_id = message_to_channel.get(ts)

    # going to be used in the GUI to determine if we should display the message
    resolved = False

    if ts in pending_messages:
        if reaction in ("white_check_mark", "+1"): # no colons in Slack reaction values
            print(f"Message {ts} has received a resolving reaction. Marking as resolved.")
            pending_messages.remove(ts)

            mark_message_resolved(channel_id, ts)

    return resolved

def get_message_content(channel_id: str, message_id: str):
    """
    Retrieves the content of a message from Slack using conversations.history

    Args:
        channel_id (str): the Slack channel ID where the message was posted
        message_id (str): the message ID/timestamp to get content from

    Returns:
        str: The content of the message
    """
    url = "https://slack.com/api/conversations.history"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {BOT_OAUTH_TOKEN}"
    }
    params = {
        "channel": channel_id,
        "latest": message_id,
        "limit": 1,
        "inclusive": True
    }

    # 10 second timeout
    ct_response = requests.get(url, headers=headers, params=params, timeout=10)
    response_data = ct_response.json()

    if not response_data.get("ok"):
        raise RuntimeError(f"Error retrieving message: {response_data['error']}")

    messages = response_data.get("messages")
    if not messages:
        raise RuntimeError("No messages found")

    return messages[0].get("text")

def mark_message_resolved(channel_id: str, ts: str):
    """
    Marks a message as resolved by appending (RESOLVED) to the message text.

    Args:
        channel_id (str): the ID of the channel containing the message
        ts (str): the timestamp of the message to update
    """
    existing_content = get_message_content(channel_id, ts)
    updated_content = f"{existing_content} (RESOLVED)"

    url = "https://slack.com/api/chat.update"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {BOT_OAUTH_TOKEN}"
    }
    payload = {
        "channel": channel_id,
        "ts": ts,
        "text": updated_content
    }

    # 10 second timeout
    res_response = requests.post(url, headers=headers, json=payload, timeout=10)
    response_data = res_response.json()

    if not response_data.get("ok"):
        raise RuntimeError(f"Error editing message: {response_data['error']}")

    print(f"Message with ID {ts} edited successfully")

    return response_data

def post_to_slack(channel_id: str, message: str):
    """
    Posts a message to Slack using chat.postMessage

    Args:
        channel (str): the Slack channel to send the message to
        message (str): the message to send
    """
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {BOT_OAUTH_TOKEN}"
    }
    payload = {
        "channel": channel_id,
        "text": message
    }

    # 10 second timeout
    post_response = requests.post(url, headers=headers, json=payload, timeout=10)
    response_data = post_response.json()

    if not response_data.get("ok"):
        raise RuntimeError(f"Error posting message: {response_data}")

    # Extract the message ID (timestamp)
    message_id = response_data.get("ts")
    pending_messages.append(message_id)
    message_to_channel[message_id] = channel_id

    print(f"Message posted with ID: {message_id}")
    
    return message_id

if __name__ == "__main__":
    # Run test
    try:
        with open("aws_json/test_post.json", "r", encoding="utf8") as test_file:
            test_event = json.load(test_file)
            response = lambda_handler(test_event, None)
            print("Response:", response)
    except FileNotFoundError as e:
        print("test_post.json not found.")
    except json.JSONDecodeError as e:
        print("Error decoding test_post.json:", e)

    try:
        with open("aws_json/test_message.json", "r", encoding="utf8") as test_file:
            test_event = json.load(test_file)
            test_event["ts"] = pending_messages[0]
            response = lambda_handler(test_event, None)
            print("Response:", response)
    except FileNotFoundError as e:
        print("test_post.json not found.")
    except json.JSONDecodeError as e:
        print("Error decoding test_post.json:", e)
