#!/usr/bin/env python3

"""
Code for interacting with AWS.

Author:
Nikki Hess (nkhess@umich.edu)
"""

import json
import boto3
from flask import Flask, request
import requests

app = Flask(__name__)

try:
    with open("aws.json", "r", encoding="utf8") as file:
        aws_config = json.load(file)
except json.JSONDecodeError as e:
    print(e)
except FileNotFoundError:
    with open("aws.json", "x", encoding="utf8") as file:
        print("aws.json not found, creating it for you...")

        defaults = {"aws_access_key": "", "aws_secret": "", "region": "us-east-2"}
        json.dump(defaults, file)
    exit()

@app.route("/sns", methods=["POST"])
def on_receive_sns_message():
    """
    Handles receiving post requests from SNS
    """

    data = request.get_json(force=True)

    print("Message received:", data)

    return {
        "statusCode": 200
    }

def post_to_slack(aws_client: boto3.client, message: str, channel_id: str, dev: bool):
    """
    Posts a message to Slack using chat.postMessage

    Args:
        aws_client (boto3.client): the AWS client we're using
        message (str): the message to send
        channel_id (str): the Slack channel to send the message to
        dev (bool): whether we're using the dev AWS instance
    """

    print("Posting message to Slack via AWS...")

    payload = {
        "body": {
            "type": "post",
            "message": message,
            "channel_id": channel_id
        }
    }
    payload = json.dumps(payload) # convert dict to string

    # the function name is apparently the name of the instance ¯\_(ツ)_/¯
    aws_client.invoke(
        FunctionName="slackLambda" + "-dev" if dev else "",
        Payload=payload
    )

def mark_message_timed_out(aws_client: boto3.client, message_id: str, channel_id: str, dev: bool):
    """
    Edits a message on Slack to mark it timed out

    Args:
        aws_client (boto3.client): the AWS client we're using
        message_id (str): the message id to edit
        channel_id (str): the Slack channel to send the message to
        dev (bool): whether we're using the dev AWS instance
    """

    print(f"Marking message {message_id} as resolved...")

    payload = {
        "body": {
            "type": "timeout",
            "message_id": message_id,
            "channel_id": channel_id
        }
    }
    payload = json.dumps(payload) # convert dict to string

    # invoke the AWS Lambda function
    aws_client.invoke(
        FunctionName="slackLabmda" + "-dev" if dev else "",
        Payload=payload
    )

def setup_aws() -> boto3.client:
    """
    Sets up the AWS client

    Returns:
        boto3.client: the AWS client
    """

    access_key = aws_config["aws_access_key"]
    secret = aws_config["aws_secret"]
    region = aws_config["region"]

    client = boto3.client(
        "lambda",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret,
        region_name=region
    )

    return client

def setup_flask(port: int):
    """
    Sets up the flask http server (to receive SNS messages)

    Args:
        port (int): the port to use
    """
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    aws = setup_aws()

    # # post_to_slack(
    # #     aws,
    # #     "This is a test from Nikki's local machine",
    # #     "C05T5H5GK54",
    # #     True
    # )

    # run the flask app
    app.run(host="0.0.0.0", port=25565)
