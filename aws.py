#!/usr/bin/env python3

"""
Code for interacting with AWS.

Author:
Nikki Hess (nkhess@umich.edu)
"""

import json
import boto3

def test_sns():
    # initialize Amazon SNS
    sns_client = boto3.client("sns", region_name="us-east-2") 

    # topic ARN
    topic_arn = ""

    # endpoint for sns
    endpoint = ""

    # create a subscription
    response = sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol="lambda",  # change protocol as needed ("http", "https", "email", "email-json", "sms", "application", "lambda", "sqs")
        Endpoint=endpoint
    )

    # Print the response
    print(response)

def post_to_slack(aws_client: boto3.client, message: str, channel_id: str, dev: bool):
    """
    Posts a message to Slack using chat.postMessage

    Args:
        aws_client (boto3.client): the AWS client we're using
        channel (str): the Slack channel to send the message to
        message (str): the message to send
        dev (bool): whether we're using the dev AWS instance
    """

    payload = {
        "type": "post",
        "message": message,
        "channel_id": channel_id
    }
    payload = json.dumps(payload) # convert dict to string

    # the function name is apparently the name of the instance ¯\_(ツ)_/¯
    aws_client.invoke(
        FunctionName="slackLambda" + "-dev" if dev else "",
        Payload=payload
    )

def setup_aws() -> boto3.client:
    """
    Sets up the AWS client

    Returns:
        boto3.client: the AWS client
    """
    try:
        with open("aws.json", "r", encoding="utf8") as file:
            aws = json.load(file)
    except json.JSONDecodeError as e:
        print(e)
    except FileNotFoundError as e:
        with open("aws.json", "x", encoding="utf8") as file:
            print("aws.json not found, creating it for you...")

            defaults = {"aws_access_key": "", "aws_secret": "", "region": "us-east-2"}
            json.dump(defaults, file)
        exit()

    access_key = aws["aws_access_key"]
    secret = aws["aws_secret"]
    region = aws["region"]

    client = boto3.client(
        "lambda",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret,
        region_name=region
    )

    return client

if __name__ == "__main__":
    aws = setup_aws()

    post_to_slack(
        aws,
        "This is a test from Nikki's local machine",
        "C05T5H5GK54",
        True
    )