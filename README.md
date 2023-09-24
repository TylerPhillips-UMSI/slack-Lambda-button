# AWS Lambda Button Press Notifier

This project captures an AWS IoT button press and sends a notification to Slack. When the button is pressed, the AWS Lambda function is triggered by the IoT event, retrieves the corresponding message from a configuration data file, and sends it as a Slack notification.

## Features

- Easily configurable
- Uses a data file for variables and options
- Verbose Cloudwatch logging
- Allows custom messages for different button IDs
- Allows button state detection with SINGLE and DOUBLE message options
- Provides a button test fuction for LONG press

## Prerequisites

- AWS Account with necessary permissions for Lambda and CloudWatch
- Slack Workspace and an incoming webhook URL
- Python installed for deployment steps
- [Seeed IoT Button For AWS](https://wiki.seeedstudio.com/SEEED-IOT-BUTTON-FOR-AWS/) 

## Setup

### 1. Configuration File

Create a configuration file (`config.json`) with the required settings:

```json
{
  "WEBHOOK_URL": "https://hooks.slack.com/services/WEBHOOK_URL",
  "BUTTON_CONFIG": {
    "BUTTON_ID": {
      "LOCATION": "Front Desk Guest Assistance",
      "MAC": "MAC_ADDRESS",
      "SINGLE": "Guest needs assistance at the Front Desk",
      "WEBHOOK_URL": null
    },
    "BUTTON": {
      "LOCATION": "Gallery Guest Assistance",
      "MAC": "MAC_ADDRESS",
      "SINGLE": "Guest needs assistance in the Gallery",
      "DOUBLE": "OPTIONAL_DOUBLE_MESSAGE",
      "WEBHOOK_URL": "ALT_URL"
    }
  }
}
```

### 2. Libraries & Packaging
This project requires additional Python libraries, specifically **requests** for sending messages to Slack. To include these libraries in your Lambda packages:

- Create a new directory for your Lambda function.
- cd (change directory) into that directory using your terminal or command prompt.
- Use pip (Python's package manager) to install the required libraries to that directory. This ensures the libraries are packaged with your Lambda function

```
  pip install requests -t .
```
- Here, -t . tells pip to install the packages to the current directory.
- Add your Lambda function script (lambda_function.py) and configuration file (config.json) to this directory.
- Zip the contents of the directory. This zip will include both your Lambda function and the required libraries.

### 3. Deploying the Lambda Function
## Manual Deployment

- Navigate to AWS Lambda in the AWS Console.
- Create a new function.
- Zip and upload the Lambda function code alongside the required libraries and config.json.
- Assign the necessary execution role.

## IoT Button Deployment

- Setup the [Seeed IoT Button For AWS](https://wiki.seeedstudio.com/SEEED-IOT-BUTTON-FOR-AWS/) using the [AWS IoT 1-Click service](https://aws.amazon.com/iot-1-click/) iOS/Android app.
- See the [Seeed Studio Wiki](https://wiki.seeedstudio.com/SEEED-IOT-BUTTON-FOR-AWS/) for detailed configuration instructions.

## Usage

After deployment, pressing the AWS IoT button should trigger the Lambda function. A single press will trigger SINGLE, a double press will trigger DOUBLE, and a long press (2-3s) will trigger LONG which sends a predefiled test message. The function will extract the button ID, get the respective message from config.json, and send it to the default Slack channel or the alternate channel provided. 

## Troubleshooting

Check CloudWatch logs for errors or issues during execution.
Ensure the IoT button is properly set up and triggering the Lambda function.
Confirm that config.json contains the correct configuration.

## Contributing

If you find any bugs or have ideas for enhancements, please open an issue or submit a pull request.

## Development Goals

**Migrate to Google sheets for button-specific configuration:** Using Google Sheets as a data source for the Lambda function would allow for a dynamic way for end users to change configurations without updating the Lambda function code or config files.

## License

This project is licensed under the MIT License.
