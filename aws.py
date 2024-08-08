#!/usr/bin/env python3

"""
Code for interacting with AWS SNS. Currently a testing ground.

Author:
Nikki Hess (nkhess@umich.edu)
"""

import boto3

# initialize Amazon SNS
sns_client = boto3.client("sns", region_name="us-east-1") 

# topic ARN
topic_arn = ""

# endpoint for sns
endpoint = ""

# create a subscription
response = sns_client.subscribe(
    TopicArn=topic_arn,
    Protocol="https",  # change protocol as needed ("http", "https", "email", "email-json", "sms", "application", "lambda", "sqs")
    Endpoint=endpoint
)

# Print the response
print(response)
