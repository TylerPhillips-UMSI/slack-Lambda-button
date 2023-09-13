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

### 2. Libraries
This project requires additional Python libraries, specifically requests for sending messages to Slack. Make sure to package the library alongside your Lambda function.

3. Deploying the Lambda Function
Manual Deployment

Navigate to AWS Lambda in the AWS Console.
Create a new function.
Zip and upload the Lambda function code alongside the required libraries and config.json.
Assign the necessary execution role.
Set up the IoT button press event trigger.
Usage

After deployment, pressing the AWS IoT button should trigger the Lambda function.
The function will extract the button ID, get the respective message from config.json, and send it to the Slack channel.
Troubleshooting

Check CloudWatch logs for errors or issues during execution.
Ensure the IoT button is properly set up and triggering the Lambda function.
Confirm that config.json contains the correct configuration.
Contributing

If you find any bugs or have ideas for enhancements, please open an issue or submit a pull request.

License

This project is licensed under the MIT License.
