#!/usr/bin/env python3

"""
Code for interacting with AWS.

Author:
Nikki Hess (nkhess@umich.edu)
"""

import json
import boto3
import requests

import concurrent.futures # for sqs polling

latest_message = None # latest SQS message

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
    response = aws_client.invoke(
        FunctionName="slackLambda" + "-dev" if dev else "",
        Payload=payload
    )

    # extract our custom response
    response = response["Payload"].read().decode("utf-8")
    response = json.loads(response)

    # this should be guaranteed with a post payload
    return response.get("posted_message_id"), response.get("posted_message_channel")

def mark_message_timed_out(aws_client: boto3.client, message_id: str, channel_id: str, dev: bool):
    """
    Edits a message on Slack to mark it timed out

    Args:
        aws_client (boto3.client): the AWS client we're using
        message_id (str): the message id to edit
        channel_id (str): the Slack channel to send the message to
        dev (bool): whether we're using the dev AWS instance
    """

    print(f"Marking message {message_id} as timed out...")

    payload = {
        "body": {
            "type": "message_timeout",
            "message_id": message_id,
            "channel_id": channel_id
        }
    }
    payload = json.dumps(payload) # convert dict to string

    # invoke the AWS Lambda function
    aws_client.invoke(
        FunctionName="slackLambda" + "-dev" if dev else "",
        Payload=payload
    )

def poll_sqs(sqs_client: boto3.client):
    """
    Periodically polls SQS, will run on a separate thread

    Args:
        sqs_client (boto3.client): the SQS client we're using
    """
    global latest_message

    queue_url = "" # fill in later pls

    while True:
        response = sqs_client.receive_message(
            QueueURL=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )

        # has to be obtained as a list first
        message = response.get("Messages", [])

        if message:
            message = message[0] # get the first item

            # process the message
            message_body = message["Body"]
            print("SQS message received:", message_body)
            latest_message = message_body

            # delete from queue after process
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message["ReceiptHandle"]
            )

def setup_aws() -> boto3.client:
    """
    Sets up the AWS client

    Returns:
        the Lambda client, the SQS client
    """

    global aws_config

    config_defaults = {"aws_access_key": "", "aws_secret": "", "region": "us-east-2"}
    try:
        with open("config/aws.json", "r", encoding="utf8") as file:
            aws_config = json.load(file)

            # if we don't have all required keys, populate the defaults
            if not all(aws_config.get(key) for key in list(config_defaults.keys())):
                with open("config/aws.json", "w", encoding="utf8") as write_file:
                    json.dump(config_defaults, write_file)
    except (FileNotFoundError, json.JSONDecodeError):
        with open("config/aws.json", "w+", encoding="utf8") as file:
            print("config/aws.json not found or wrong, creating + populating defaults...")

            json.dump(config_defaults, file)
            print("Please fill out config/aws.json before running again.")
        exit()

    access_key = aws_config["aws_access_key"]
    secret = aws_config["aws_secret"]
    region = aws_config["region"]

    # set up lambda client
    client = boto3.client(
        "lambda",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret,
        region_name=region
    )

    # set up sqs client
    sqs_client = boto3.client(
        "sqs",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret,
        region_name=region
    )
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(poll_sqs, sqs_client)

    return client, sqs_client

if __name__ == "__main__":
    lambda_client, sqs_client = setup_aws()

    # # post_to_slack(
    # #     aws,
    # #     "This is a test from Nikki's local machine",
    # #     "C05T5H5GK54",
    # #     True
    # )
