import boto3
import json
import datetime
import dateutil.parser
import re
import time

valid_locations = ["manhattan"]
valid_slots = ["Location", "Cuisine", "NumberOfPeople", "Date", "Time", "PhoneNumber"]
valid_cuisines = ["american", "mexican", "japanese", "spanish", "indian", "chinese", "italian", "ethiopian", "french"]
valid_nums = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "11": 11, "12": 12, "13": 13, "14": 14, "15": 15, "16": 16, "17": 17, "18": 18, "19": 19, "20": 20}

USER_INFO_TABLE_NAME = 'user-history'

def validate_and_reply(slot_type, user_input, reservation_template):
    valid = False
    error_msg = ""
    try:
        '''
        location manhattan.trim().lower()
        //check time valid ie greater than current time


        '''
        if slot_type == "Location":
            if user_input.strip().lower() in valid_locations:
                valid = True
            else:
                error_msg =  "Sorry, we only serve from the following locations currently: {}".format(", ".join(valid_locations))
                valid=False
        elif slot_type == "Cuisine":
            if user_input.strip().lower() in valid_cuisines:
                valid = True
            else:
                error_msg =  "Sorry, we only serve from the following cuisines currently: {}.".format(", ".join(valid_cuisines))
                valid=False
        elif slot_type == "NumberOfPeople":
            if user_input.strip().lower() in valid_nums:
                valid = True
            else:
                error_msg =  "Sorry, but the maximum size of the party is 20. Please choose a number between 1 and 20."
                valid=False
        elif slot_type == "Date":
            if dateutil.parser.parse(user_input).date() >= datetime.date.today():
                valid = True
            else:
                error_msg =  "Please enter a valid date."
                valid=False
        elif slot_type == "Time":
            try:
                correct_time = dateutil.parser.parse(user_input).timestamp()
                valid = True
            #     if dateutil.parser.parse(reservation_template["Date"]).date() == datetime.date.today():
            #         if correct_time > int(time.time()):
            #             valid = True
            except:
                valid = False
                error_msg =   "Please enter a valid time."
            # print("Yash Time ",correct_time,time.time(),valid)
        elif slot_type == "EmailId":
            email_regex = "^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$"
            if re.match(email_regex, user_input):
                valid = True
            else:
                valid = False
                error_msg =  "Please enter a valid email id."
        elif slot_type == "PhoneNumber":
            if len(user_input) == 10 and user_input.isnumeric():
                valid = True
            else:
                valid = False
                error_msg =  "Please enter a valid phone number."

    except ValueError:
        valid = False 
        error_msg = ""
        

    return valid, error_msg

def json_response(event, content, dialogActionType='Close', fulfillmentState='Fulfilled'):
    if event['sessionAttributes'] is not None:
        session_attributes = event['sessionAttributes']
    else:
        session_attributes = {}
    
    json_resp = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': dialogActionType,
            'fulfillmentState': fulfillmentState,
            'message': {
                'contentType': 'PlainText',
                'content': content
            }
        }
    }
    return json_resp


def handle_dining_suggestions(event):

    # we need to fill in the template
    reservation_template = dict.fromkeys(valid_slots)
    for slot in valid_slots:
        # check if slot exists
        if event['currentIntent']['slots'].get(slot) is None:
            json_resp = json_response(
                event=event,
                content="",
                dialogActionType="Delegate",
            )
            try:
                json_resp['dialogAction'].pop('message', None)
                json_resp['dialogAction'].pop('fulfillmentState', None)
            except:
                print("No Key")

            json_resp['dialogAction']['slots'] = reservation_template
            print("Dining Yash: ",json_resp)
            return json_resp

        valid, error_msg = validate_and_reply(slot, event['currentIntent']['slots'].get(slot), reservation_template)
        if not valid:
            # if the response is wrong
            json_resp = json_response(
                event=event,
                content=error_msg,
                dialogActionType="ElicitSlot",
            )
            try:
                json_resp['dialogAction'].pop('fulfillmentState', None)
            except:
                print("No Key")

            json_resp['dialogAction']['intentName'] = 'DiningSuggestionsIntent'
            json_resp['dialogAction']['slots'] = reservation_template
            json_resp['dialogAction']['slotToElicit'] = slot

            return json_resp
        else:
            # everything is OK
            if slot == "NumberOfPeople":
                reservation_template[slot] = valid_nums[event['currentIntent']['slots'].get(slot)]
            else:
                reservation_template[slot] = event['currentIntent']['slots'].get(slot)
        
        


    send_to_sqs(reservation_template)
    # old_suggestion = get_old_recommendations(reservation_template['PhoneNumber'])
    
    json_resp = json_response(
        event=event,
        content="You’re all set. Expect my suggestions shortly! Have a good day."
    )

    return json_resp


# def get_old_recommendations(phone):
#     client = boto3.resource('dynamodb')
#     table = client.Table(USER_INFO_TABLE_NAME)
    
#     print("Getting ID: {}".format(id))
#     response = table.get_item(Key={'phone': phone})
#     if 'Item' not in response:
#         print('User not yet present in the sessions database')
#         return None
    
#     suggestion = response['Item']
#     return {
#         'phone': suggestion['phone'],
#         'cuisine': suggestion['cuisine'],
#         'location': suggestion['location'],
#         'message': suggestion['message']
#     }



def send_to_sqs(reservation_json_response):

    client = boto3.client('sqs')
    url = client.get_queue_url(QueueName="Q1")['QueueUrl']
    print("send_to_sqs Yash",reservation_json_response)
    if "EmailId" in reservation_json_response:
        reservation_json_response['PhoneNumber'] = reservation_json_response['EmailId']
        del reservation_json_responsex['EmailId']
    
    try:
        response = client.send_message(QueueUrl=url, MessageBody=json.dumps(reservation_json_response))
        print("SQS Response: {}".format(response))
    except:
        print("SQS Error")




def handle_intents(current_intent, event):
    if current_intent == "GreetingIntents":
        content = "Hello there, how can I help you?"
        state = "Fulfilled"
        return json_response(event, content, fulfillmentState=state)
    elif current_intent == "ThanksYouIntent":
        content = "Thank you for using the Dining Concierge service."
        state = "Fulfilled"
        return json_response(event, content, fulfillmentState=state)
    elif current_intent == "DiningSuggestionsIntents":
        return handle_dining_suggestions(event)
    else:
        content = "Failed to recognize the intent."
        state = "Failed"
        return json_response(event, content, fulfillmentState=state)

    # return json_response(event, content, fulfillmentState=state)

def lambda_handler(event, context):
    current_intent = event["currentIntent"]["name"]
    print("yash look here",event)
    print("context: ",context)

    return handle_intents(current_intent, event)

