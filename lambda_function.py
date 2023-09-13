import json
import requests

# Your Slack webhook URL
WEBHOOK_URL = 'YOUR_SLACK_WEBHOOK_URL'

# Button to message mapping
# Syntax is 'deviceId':'message'
BUTTON_MESSAGE_MAP = {
    'BUTTON_ID_1': 'Message for Button 1',
    'BUTTON_ID_2': 'Message for Button 2'
    .
    .
    .
}

def post_to_slack(message):
    payload = {
        'text': message
    }
    response = requests.post(WEBHOOK_URL, data=json.dumps(payload))
    return response.text

def test_slack_webhook():
    test_message = "Lambda testing Slack webhook"
    response = requests.post(WEBHOOK_URL, data=json.dumps({'text': test_message}), headers={'Content-Type': 'application/json'})

    if response.status_code == 200:
        return "Webhook is reachable and working!"
    else:
        return f"Failed to reach webhook. Response: {response.text}"

def lambda_handler(event, context):
    # Print the entire event to understand its structure
    print(event)

    # Retrieving deviceId from nested structure in the event
    deviceInfo = event.get('deviceInfo', {})
    deviceId = deviceInfo.get('deviceId', None)

    # Trim any whitespace from the deviceId
    if deviceId:
        deviceId = deviceId.strip()

    print(f"Extracted deviceId: {deviceId}")  # Logging the extracted deviceId

    if not deviceId:
        print('No deviceId provided.')
        return {
            'statusCode': 400,
            'body': 'No deviceId provided.'
        }

    message = BUTTON_MESSAGE_MAP.get(deviceId, 'Unknown button pressed.')
    print(f"Retrieved message from BUTTON_MESSAGE_MAP: {message}")  # Log the retrieved message for debugging
    print("About to send message to Slack...")
    slack_response = post_to_slack(message)
    print(f"Received response from Slack: {slack_response}")

    # Finally, check the internet access
    try:
        response = requests.get('http://www.google.com', timeout=5)
        if response.status_code == 200:
            print('Internet Access Confirmed')
        else:
            print(f"Unexpected status code from Google: {response.status_code}")
    except requests.RequestException as e:
        print(f"No Internet. Error: {str(e)}")

    return {
        'statusCode': 200,
        'body': slack_response
    }
