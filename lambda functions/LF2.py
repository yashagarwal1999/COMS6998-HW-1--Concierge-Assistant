from http import client
import json
import random 
import boto3
import requests

USER_INFO_TABLE_NAME = 'user-history'

SLOT_VALUES = ["Location", "Cuisine", "NumberOfPeople", "Date", "Time", "PhoneNumber"]
SOURCE_MAIL = 'yashagarwal19991@gmail.com'

RESTAURANT_TABLE_NAME = 'yelp-restaurants'

HEADERS = { "Content-Type": "application/json" }
NUMBER_OF_RECOMMENDATIONS = 3


AWSAUTH = ('', '')

OPEN_SERVICE_URL = ''
SQS_QUEUE_NAME = ''

def push_user_history(curr_reservation, final_msg):
    client = boto3.resource('dynamodb')
    dynamodb = client.Table(USER_INFO_TABLE_NAME)
    email = "yashagarwal19991@gmail.com"

    dynamodb.put_item(Item={
        "emailid": email,
        "location": curr_reservation["Location"],
        "cuisine": curr_reservation["Cuisine"],
        "message": "Previously, I had sent the following: \n" + final_msg
    })
    

def get_resp_from_client(client, args, job):
    if job == "sqs":
        response = client.receive_message(
            QueueUrl=args,
            AttributeNames=['All'],
            MessageAttributeNames=SLOT_VALUES,
            MaxNumberOfMessages=1,
            VisibilityTimeout=1,
            WaitTimeSeconds=1
        )
    
    if job == "recs":
        response = requests.get(OPEN_SERVICE_URL.format(args["Cuisine"]), auth=AWSAUTH, headers=HEADERS)
        response = response.json()
    
    return response

def rec_to_json(rec_list):
    recs = []
    for rec in rec_list:
        json_recs = {}
        json_recs["id"] = rec["_source"]["id"]
        json_recs["cuisine"] = rec["source"]["cuisine"]
        recs.append(json_recs)
    return recs

def get_reservations_from_sqs():

    client = boto3.client('sqs')
    url = client.get_queue_url(QueueName=SQS_QUEUE_NAME)['QueueUrl']
    resp_from_client = get_resp_from_client(client, url, "sqs")

    if 'Messages' in resp_from_client:
        current_reservations = []
        for msg in resp_from_client:
            msg_body = json.loads(msg["Body"])
            curr_reservation = {}
            for slot in SLOT_VALUES:
                curr_reservation[slot] = msg_body[slot]
                curr_reservation['ReceiptHandle'] = msg['ReceiptHandle']
            current_reservations.append(curr_reservation)
    else:
        return []

    return current_reservations

def get_restaurant_recs(curr_reservation):
    resp = get_resp_from_client(None, curr_reservation, "recs")
    recs = resp["hits"]["hits"]
    if len(recs) >= NUMBER_OF_RECOMMENDATIONS:
        recs = random.choice(recs, NUMBER_OF_RECOMMENDATIONS)
    recs = rec_to_json(recs)
    return recs


def query_dynamo_db(index_id):
    client = boto3.resource('dynamodb')
    dynamodb = client.Table(RESTAURANT_TABLE_NAME)

    resp = dynamodb.get_item(Key={'id': index_id})
    if "Item" in resp:
        resp_id = {
            "id": resp["Item"]["id"],
            "name": resp["Item"]["name"],
            "address": resp["Item"]["address"],
        }
    else:
        return None
    
    return resp_id


def build_message(recs, curr_reservation):
    msg = ""
    idx = 1
    for rec in recs:
        restaurant_details = query_dynamo_db(rec["id"])
        if restaurant_details is not None:
            msg += "{}. Name: {}, located at {} \n".format(idx, restaurant_details["name"], restaurant_details["address"])
        idx += 1

    final_msg = "Hello, here are my suggestions for a {} restaurant for {} people for {} at {}".format(curr_reservation["Cuisine"], curr_reservation["NumberOfPeople"], curr_reservation["Date"], curr_reservation["Time"])

    final_msg += msg
    final_msg += "Enjoy your meal!"

    return final_msg

def push_to_ses(msg_for_reservation, phone_num):
    phone_num = "yashagarwal19991@gmail.com"
    if True:
        client = boto3.client('ses', region_name='us-east-1')
        response = client.send_email(
        Source=SOURCE_MAIL,
        SourceArn='{}'.format("arn:aws:ses:us-east-1:710244106907:identity/yashagarwal19991@gmail.com"),
        Destination={
            'ToAddresses': [phone_num],
            'CcAddresses': [],
            'BccAddresses': []
        },
        Message={
            'Subject': {
                'Data': 'Dining Concierge Suggestions',
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': msg_for_reservation,
                    'Charset': 'UTF-8'
                }
            }
        }
    )


def clear_reservations_from_sqs(current_reservations):
    client = boto3.client('sqs')
    url = client.get_queue_url(QueueName=SQS_QUEUE_NAME)['QueueUrl']
    for curr_reservation in current_reservations:
        resp = client.delete_message(
            QueueUrl=url,
            ReceiptHandle=curr_reservation['ReceiptHandle']
        )


def get_recommendations(current_reservations):
    for curr_reservation in current_reservations:
        restaurant_recs = get_restaurant_recs(curr_reservation) # list of {id, cuisine}
        msg_for_reservation = build_message(restaurant_recs, curr_reservation)
        push_to_ses(msg_for_reservation, curr_reservation["PhoneNumber"])
        push_user_history(curr_reservation, msg_for_reservation)


    
def lambda_handler(event, context):

    current_reservations = get_reservations_from_sqs()
    get_recommendations(current_reservations) 
    clear_reservations_from_sqs(current_reservations)
