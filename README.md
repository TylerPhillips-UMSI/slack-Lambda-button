# AWS IoT Button Press Slack Notifier via Lambda Function

This project integrates the AWS IoT button with Slack to create an on-demand alert system. Designed primarily as a silent assistance request mechanism, it serves two main use-cases:

1. **Guest Help**: Allows guests or visitors to signal for assistance.
2. **Staff Assistance**: Acts as an internal signaling system, especially when staff members find themselves in situations where they might need immediate help from another adult on-site.

Depending on the button's configuration, different messages can be sent to designated Slack channels, giving both flexibility and specificity in communication.

## Features

- **Easily Configurable**: Customize button actions and messages through a simple JSON file.
- **Verbose CloudWatch Logging**: Gain insights into button presses, messages, and potential errors in real-time.
- **Dynamic Slack Webhook**: Send notifications to different Slack channels or workspaces based on button configuration.
- **Rate Limiting**: Prevents button spam by enforcing a 1 minute cooldown period between messages.

## Prerequisites

- AWS Account with necessary permissions for Lambda, IoT, and CloudWatch
- Slack Workspace with a configured incoming webhook
- Python installed for deployment steps
- <a href="https://wiki.seeedstudio.com/SEEED-IOT-BUTTON-FOR-AWS/" target="_blank">Seeed IoT Button For AWS</a>

## Setup

### 1. Slack Bot Setup

- Create a new <a href="https://api.slack.com/apps" target="_blank">Slack App</a>.
- Under Features, activate `Incoming Webhooks`.
- Add a new webhook to your workspace. Copy the webhook URL, which will be used in the `config.json`.

### 2. Configuration File

Create a configuration file (`config.json`) with the required settings. Expand this file to meet the number of buttons you are deploying:

```
{
  "WEBHOOK_URL": "https://hooks.slack.com/services/WEBHOOK_URL",
  "BUTTON_CONFIG": {
    "DEVICE_ID": {
      "LOCATION": "Front Desk Guest Assistance",
      "MAC": "MAC_ADDRESS",
      "SINGLE": "Guest needs assistance at the Front Desk",
      "WEBHOOK_URL": null
    },
    "DEVICE_ID": {
      "LOCATION": "Gallery Guest Assistance",
      "MAC": "MAC_ADDRESS",
      "SINGLE": "Guest needs assistance in the Gallery",
      "DOUBLE": "OPTIONAL_DOUBLE_MESSAGE",
      "WEBHOOK_URL": "ALT_URL",
    }
  }
}
```

In the example file above the following are all user-filled values:
 - WEBHOOK_URL
 - DEVICE_ID
 - LOCATION
 - MAC
 - ALT_URL

### 3. Libraries & Packaging

This project requires the `requests` Python library to send messages to Slack. 

To package this library with your Lambda function:
- Create a new directory for your Lambda function.
- Change into that directory using your terminal or command prompt.
- Install the required libraries into that directory:

```
  pip install requests -t .
```

- Add your Lambda function script (lambda_function.py) and configuration file (config.json) to this directory.
- Zip the contents of the directory, ensuring the libraries are included.

### 4. Deploying the Lambda Function

#### Manual Deployment

- Navigate to AWS Lambda in the AWS Console.
- Create a new function.
- Zip and upload the Lambda function code alongside the required libraries and config.json.
- Assign the necessary execution role.

#### IoT Button Deployment

- Set up the <a href="https://wiki.seeedstudio.com/SEEED-IOT-BUTTON-FOR-AWS/" target="_blank">Seeed IoT Button For AWS</a> using the <a href="https://aws.amazon.com/iot-1-click/" target="_blank">AWS IoT 1-Click service</a> iOS/Android app.
- For detailed configuration instructions, refer to the <a href="https://wiki.seeedstudio.com/SEEED-IOT-BUTTON-FOR-AWS/" target="_blank">Seeed Studio Wiki</a>.

## Usage

After deployment, pressing the AWS IoT button will trigger the Lambda function. Depending on the type of press, a specific message from `config.json` will be sent to Slack. 

## Troubleshooting

- Check CloudWatch logs for errors or issues during execution.
- Ensure the IoT button is properly set up and triggering the Lambda function.
- Confirm that `config.json` contains the correct configurations.
- Verify the function isn't affected by the rate limit of 1 message per minute which is applied per-button. You can verify this in the CloudWatch logs. Please note that if you need to modify the rate limit it is presently hard-coded in `lambda_function.py`. Future revisions will move this option to `config.json`.

## Contributing

If you find any bugs or have ideas for enhancements, please open an issue or submit a pull request.

## Development Goals

- **Migrate to Google sheets for button-specific configuration:** (planned) This would allow users to dynamically change configurations without updating the Lambda function code or config files.
- **User-Definable Rate Limiting:** Make the rate limit user-definable in the configuration file and not hard-coded to the function.
- **Slack Bot Commands:** Enable a test / setup mode that disregards button presses for a user-definable period. This would prevent false alerts from being posted while the buttons are deployed.

## Credits

Collaborators on this project include <a href="https://openai.com" target="_blank">ChatGPT by OpenAI</a>.

## License

This project is licensed under the MIT License.
