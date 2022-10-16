import json
import boto3
import datetime

def lambda_handler(event, context):
    print("Event: {}".format(event))
    userMessage = event["messages"][0]["unstructured"]["text"]
    client = boto3.client("lex-runtime")
    print("Yash lf0 ",event,context)
    response = client.post_text(
        botName='DiningConcierge',
        botAlias='DiningConciergeNewAlias',
        userId='ya2467',
        inputText=userMessage
    )
    
    message = response.get('message', None)
    if message is not None:
        return {
            "messages": [
              {
                "type": "unstructured",
                "unstructured": {
                  "id": "0",
                  "text": message,
                  "timestamp": datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                }
              }
            ]
        }
    
    return {
        'code': 0,
        'message': 'Dining Concierge bot is unavailable right now. Please check back later.'
    }