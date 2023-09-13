# AWS Lambda Button Press Notifier

This project captures an AWS IoT button press and sends a notification to Slack. When the button is pressed, the AWS Lambda function is triggered by the IoT event, retrieves the corresponding message from a configuration data file, and sends it as a Slack notification.

## Features

- **Simplicity**: Easily configurable for both tech-savvy and novice users.
- **Security**: Avoids hard-coded credentials or secrets; uses a data file for configurations.
- **Flexibility**: Allows custom messages for different button IDs.

## Prerequisites

- AWS Account with necessary permissions for Lambda and CloudWatch.
- Slack Workspace and an incoming webhook URL.
- AWS CLI installed and configured (for deployment steps).

## Setup

### 1. Configuration File

Create a configuration file (`config.json`) with the required settings:

```json
{
  "WEBHOOK_URL": "YOUR_SLACK_WEBHOOK_URL",
  "BUTTON_MESSAGE_MAP": {
    "BUTTON_ID_1": "Message for Button 1",
    "BUTTON_ID_2": "Message for Button 2"
  }
}
