#!/usr/bin/env python3

"""
The AWS Lambda function code, not to be used locally.

Author:
Nikki Hess (nkhess@umich.edu)
"""

import json
import requests
from threading import Timer
import boto3

# Read the configuration files
try:
    with open("config/slack.json", "r", encoding="utf8") as file:
        CONFIG = json.load(file)
except json.JSONDecodeError as e:
    print(e)
except FileNotFoundError as e:
    with open("config/slack.json", "x", encoding="utf8") as file:
        print("config/slack.json not found, creating it for you...")

        defaults = {"bot_oauth_token": "", "button_config": {"device_id": ""}}
        json.dump(defaults, file)


CONFIG_DEFAULTS = {"aws_access_key": "", "aws_secret": "", "region": "us-east-2"}
try:
    with open("config/aws.json", "r", encoding="utf8") as file:
        AWS_CONFIG = json.load(file)

        # if we don't have all required keys, populate the defaults
        if not all(AWS_CONFIG.get(key) for key in list(CONFIG_DEFAULTS.keys())):
            with open("config/aws.json", "w", encoding="utf8") as write_file:
                json.dump(CONFIG_DEFAULTS, write_file)
except (FileNotFoundError, json.JSONDecodeError):
    with open("config/aws.json", "w+", encoding="utf8") as file:
        print("config/aws.json not found or wrong, creating + populating defaults...")

        json.dump(CONFIG_DEFAULTS, file)
        print("Please fill out config/aws.json before running again.")
    exit()

ACCESS_KEY = AWS_CONFIG["aws_access_key"]
SECRET = AWS_CONFIG["aws_secret"]
REGION = AWS_CONFIG["region"]
SNS_ARN = AWS_CONFIG["sns_arn"]

# set up sns client
SNS_CLIENT = boto3.client(
    "sns",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET,
    region_name=REGION
)

BUTTON_CONFIG = CONFIG["button_config"]
BOT_OAUTH_TOKEN = CONFIG["bot_oauth_token"]

pending_messages = []
message_to_channel = {} # pairs message ids with channel ids
message_to_device_id = {} # pairs message ids with device ids

def lambda_handler(event: dict, context: object):
    """
    AWS Lambda function entry point.

    Args:
        event (dict): the event data from Slack
        context (object): the runtime information

    Returns:
        dict: a response object for the HTTP request
    """
    event_body = event.get("body", "{}")

    # slack sends body as a json-string, but our local test code doesn't
    # so let's handle both here
    if isinstance(event_body, str):
        event_body = json.loads(event_body)

    event_type = event_body.get("type")

    # slack url verification
    # respond with the challenge to verify the url
    if event_type == "url_verification":
        return {
            "statusCode": 200,
            "body": event_body.get("challenge", "")
        }
    # if we're not doing URL verification, we need to go one level deeper
    elif event_type == "event_callback":
        event_body = event_body.get("event", "{}")
        event_type = event_body.get("type")

    print("type:", event_type)
    posted_message_id = None
    posted_message_channel = None

    # according to THIS page: https://api.slack.com/events/message/message_replied
    # there is a bug where subtype is currently missing when the event is
    # dispatched via the events API. until fixed, we need to verify that it has a thread_ts,
    # which is unique to message replies here
    if event_type == "message" and event_body.get("thread_ts") is not None:
        # this is awful :(
        message = event_body.get("text")
        handle_message_replied(event_body, message)
    elif event_type == "reaction_added":
        message = event_body.get("reaction", "")
        handle_reaction_added(event_body)
    elif event_type == "post":
        channel_id = event_body.get("channel_id", "")
        message = event_body.get("message", "")
        device_id = event_body.get("device_id", "")
        posted_message_id, posted_message_channel = post_to_slack(channel_id, message, device_id)
    elif event_type == "message_timeout":
        channel_id = event_body.get("channel_id", "")
        message_id = event_body.get("message_id", "")
        message = "message_timeout"
        message_timeout(channel_id, message_id)
    else:
        return {
            "statusCode": 404
        }

    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/plain"
        },
        "body": message,
        "posted_message_id": posted_message_id or None,
        "posted_message_channel": posted_message_channel or None
    }

    return response

def get_user_display_name(user_id: str):
    """
    Gets a user's display name from Slack via their ID, falls back on real name

    Args:
        user_id (str): the user ID to gather info on

    Returns:
        str: the user's display name/real name/Unknown
    """
    url = "https://slack.com/api/users.info"
    headers = {
        "Authorization": f"Bearer {BOT_OAUTH_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }
    params = {
        "user": user_id
    }

    # 10 second timeout
    response = requests.get(url, headers=headers, params=params, timeout=10)
    user_info = response.json()

    if not user_info.get("ok"):
        raise RuntimeError(f"Error retrieving message: {user_info['error']}")

    user_name = user_info["user"].get("real_name", "Unknown")
    display_name = user_info["user"]["profile"].get("display_name", user_name)

    return display_name

def handle_message_replied(event: dict, reply_text: str) -> bool:
    """
    Handles messages for lambda_handler

    Args:
        event (dict): the event data from Slack
        reply_text (str): the text content of the message reply

    Returns:
        resolved (bool): whether the message was marked as resolved, for GUI
    """
    print("Handling message...")

    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")

    # gather information about the author
    author_id = event.get("user")
    author_name = get_user_display_name(author_id)

    # going to be used in the GUI to determine if we should display the message
    resolved = False

    sns_message = {
        "ts": thread_ts,
        "reply_text": reply_text,
        "reply_author": author_name
    }

    if thread_ts in pending_messages:
        if ":white_check_mark:" in reply_text or ":+1:" in reply_text:
            print(f"Message thread {thread_ts} has received a resolving response. Marking as resolved.")
            pending_messages.remove(thread_ts)

            message_append(channel_id, thread_ts, "*(resolved)*")

            SNS_CLIENT.publish(
                TopicArn=SNS_ARN,
                Message=json.dumps(sns_message),
                MessageGroupId=message_to_device_id[thread_ts], # original device
                Subject="Message Resolved Notification"
            )

            resolved = True
        else:
            SNS_CLIENT.publish(
                TopicArn=SNS_ARN,
                Message=json.dumps(sns_message),
                MessageGroupId=message_to_device_id[thread_ts], # original device
                Subject="Message Reply Notification"
            )
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
    print("Handling reaction added...")

    reaction = event.get("reaction")
    item = event.get("item", {})
    message_id = item.get("ts")
    channel_id = message_to_channel.get(message_id)

    # going to be used in the GUI to determine if we should display the message
    resolved = False

    # gather information about the author
    author_id = event.get("user")
    author_name = get_user_display_name(author_id)

    if message_id in pending_messages:
        # no colons in Slack reaction values
        # +1 in reaction because there are multiple possible skin tones
        if reaction == "white_check_mark" or "+1" in reaction:
            print(f"Message {message_id} has received a resolving reaction. Marking as resolved.")
            pending_messages.remove(message_id)

            message_append(channel_id, message_id, "*(resolved)*")

            sns_message = {
                "ts": message_id,
                "reply_text": reaction,
                "reply_author": author_name
            }

            SNS_CLIENT.publish(
                TopicArn=SNS_ARN,
                Message=json.dumps(sns_message),
                MessageGroupId=message_to_device_id[message_id], # original device
                Subject="Message Resolved Notification"
            )
        else:
            print("Reaction was not white_check_mark or +1")
    else:
        print("Timestamp was not in pending messages")

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

def message_append(channel_id: str, ts: str, to_append: str):
    """
    Marks a message as resolved by appending (resolved) to the message text.

    Args:
        channel_id (str): the ID of the channel containing the message
        ts (str): the timestamp of the message to update
    """
    existing_content = get_message_content(channel_id, ts)
    updated_content = f"{existing_content} {to_append}"

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

def post_to_slack(channel_id: str, message: str, device_id: str):
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

    print(channel_id)

    # 10 second timeout
    post_response = requests.post(url, headers=headers, json=payload, timeout=10)
    response_data = post_response.json()

    if not response_data.get("ok"):
        raise RuntimeError(f"Error posting message: {response_data}")

    # Extract the message ID (timestamp)
    message_id = response_data.get("ts")
    pending_messages.append(message_id)
    message_to_channel[message_id] = channel_id
    message_to_device_id[message_id] = device_id

    print(f"Message posted with ID: {message_id}")

    return message_id, channel_id

def message_timeout(channel_id: str, message_id: str):
    """
    Marks a message as timed out (usually after 3 minutes)
    Args:
        channel_id (str): the Slack channel ID where the message was posted
        message_id (str): the message ID/timestamp to get content from
    """
    if message_id in pending_messages:
        pending_messages.remove(message_id)
        message_append(channel_id, message_id, "*(timed out)*")

        print(f"Message {message_id} has timed out")

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
    