#!/usr/bin/env python3

"""
Code for interacting with AWS.

Author:
Nikki Hess (nkhess@umich.edu)
"""

import threading # for sqs polling

import json
import boto3

LATEST_MESSAGE = None # latest SQS message

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
    global LATEST_MESSAGE

    queue_url = "https://sqs.us-east-2.amazonaws.com/225753854445/slackLambda-dev.fifo"

    while True:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )

        # has to be obtained as a list first
        message = response.get("Messages", [])

        if message:
            message = message[0] # get the first item

            # process the message
            message_body = message["Body"]
            message_body = json.loads(message_body) # load into JSON
            message_body = message_body["Message"]
            message_body = json.loads(message_body) # load into JSON again

            print("SQS message received:", message_body)
            LATEST_MESSAGE = message_body

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
    global AWS_CONFIG

    config_defaults = {"aws_access_key": "", "aws_secret": "", "region": "us-east-2"}
    try:
        with open("config/aws.json", "r", encoding="utf8") as file:
            AWS_CONFIG = json.load(file)

            # if we don't have all required keys, populate the defaults
            if not all(AWS_CONFIG.get(key) for key in list(config_defaults.keys())):
                with open("config/aws.json", "w", encoding="utf8") as write_file:
                    json.dump(config_defaults, write_file)
    except (FileNotFoundError, json.JSONDecodeError):
        with open("config/aws.json", "w+", encoding="utf8") as file:
            print("config/aws.json not found or wrong, creating + populating defaults...")

            json.dump(config_defaults, file)
            print("Please fill out config/aws.json before running again.")
        exit()

    access_key = AWS_CONFIG["aws_access_key"]
    secret = AWS_CONFIG["aws_secret"]
    region = AWS_CONFIG["region"]

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
   
    polling_thread = threading.Thread(target=poll_sqs, args=(sqs_client,), daemon=True)
    polling_thread.start()

    return client, sqs_client

if __name__ == "__main__":
    lambda_client, sqs_client = setup_aws()

    while True:
        pass

    # # post_to_slack(
    # #     aws,
    # #     "This is a test from Nikki's local machine",
    # #     "C05T5H5GK54",
    # #     True
    # )
