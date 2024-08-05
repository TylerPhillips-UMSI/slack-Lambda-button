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
    body = event["body"]

    slack_event = json.loads(body)

    event_type = slack_event["event"]["type"]
    if event_type == "message":
        handle_message(slack_event["event"])
    elif event_type == 'reaction_added':
        handle_reaction_added(slack_event['event'])
    elif event_type == 'post':
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

    # going to be used in the GUI to determine if we should display the message
    resolved = False

    if thread_ts in pending_messages:
        if ":white_check_mark:" in message or ":+1:" in message:
            print(f"Message thread {thread_ts} has received a resolving response. Marking as resolved.")
            pending_messages.remove(thread_ts)

            resolved = True

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

    # going to be used in the GUI to determine if we should display the message
    resolved = False

    if ts in pending_messages:
        if reaction in ("white_check_mark", "+1"): # no colons in Slack reaction values
            print(f"Message {ts} has received a resolving reaction. Marking as resolved.")
            pending_messages.remove(ts)

    return resolved

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
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    response_data = response.json()

    if not response_data.get("ok"):
        raise Exception(f"Error posting message: {response_data}")

    # Extract the message ID (timestamp)
    message_id = response_data.get("ts")
    pending_messages.append(message_id)

    print(f"Message posted with ID: {message_id}")
    
    return message_id