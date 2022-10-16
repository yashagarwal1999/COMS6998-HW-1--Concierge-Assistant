import sys
import json
import json
import boto3
import string
import requests
import datetime

from urllib.error import HTTPError
from urllib.parse import quote

CUISINES = ["indian", "chinese", "italian", "ethiopian", "french", "american", "mexican", "japanese", "spanish"]
LOCATION = 'Manhattan, NY'
SEARCH_LIMIT = 50

API_KEY = ''
API_HOST = 'https://api.yelp.com'
SEARCH_PATH = '/v3/businesses/search'

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
TABLE_NAME = 'yelp-restaurants'



def get_english_name(restaurant_name):
    printable = set(string.printable)
    english_name = ''.join(filter(lambda x: x in printable, restaurant_name))
    return english_name




def get_api_response(cuisine, offset):
    url_params = {
        'term': "{} restaurant".format(cuisine).replace(' ', '+'),
        'location': LOCATION.replace(' ', '+'),
        'limit': SEARCH_LIMIT,
        'offset': offset
    }
    url_params = url_params or {}
    url = '{0}{1}'.format(API_HOST, quote(SEARCH_PATH.encode('utf8')))
    headers = {
        'Authorization': 'Bearer %s' % API_KEY,
    }
    response = requests.request('GET', url, headers=headers, params=url_params)
    return response.json()

def get_restaurant_address(restaurant):
    return str(" ".join(restaurant['location'].get('display_address', [])))

def get_data_from_restaurant_dict(restaurant,cuisine):
    businessID = restaurant['id']
    name = None
    zip_code = None

    if 'name' in restaurant:
        name = restaurant['name']
    name =get_english_name(name)

    if "zip_code" in restaurant:
        zip_code = restaurant['location']['zip_code']
    address = get_restaurant_address(restaurant)
    rating =0

    if "rating" in restaurant:
        rating =int(restaurant['rating'])
    
    review_count =0
    if "review_count" in restaurant:
        review_count = restaurant['review_count']
    
    is_closed = True
    if "is_closed" in restaurant:
        is_closed = restaurant["is_closed"]
    
    phone = None
    if "phone" in restaurant:
        phone = restaurant["phone"]
    
    image_url = ""
    if "image_url" in restaurant:
        image_url = restaurant["image_url"]
    
    inserted_at_timestamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f")


    return {
        'id': businessID,
        'cuisine': cuisine,
        'name': name,
        'address': address,
        'zip_code': zip_code,
        'rating': rating,
        'review_count': review_count,
        'is_closed': is_closed,
        'phone': phone,
        'image_url': image_url,
        'inserted_at_timestamp': inserted_at_timestamp
    }

def send_data_to_dynamoDb():
    client = boto3.resource('dynamodb', region_name='us-east-1', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    table = client.Table(TABLE_NAME)
    
    for cuisine in CUISINES:
        with open('./restaurants/{}_data.json'.format(cuisine), 'r') as f:
            restaurants = json.load(f)
            for index, restaurant in enumerate(restaurants):
                print('{}/{} {} restaurant put in the DB'.format(index, len(restaurants), cuisine))
                restaurant_info_dict = get_data_from_restaurant_dict(restaurant,cuisine)

                if restaurant['coordinates']:
                    restaurant_info_dict['latitude'] = str(restaurant['coordinates']['latitude'])
                    restaurant_info_dict['longitude'] = str(restaurant['coordinates']['longitude'])
                
                
                table.put_item(Item=restaurant_info_dict)

def get_all_restaurants_of_one_cuisine(cuisine):
    list_of_restaurants = []
    offset = 0
    total_number_of_restauranst_possible = 1000
    while len(list_of_restaurants)<=total_number_of_restauranst_possible:
        response = get_api_response(cuisine,offset)
        if total_number_of_restauranst_possible > response.get('total',1000):
            total_number_of_restauranst_possible = response.get('total',1000)
        
        restaurants_in_response = response.get('businesses',None)
        if restaurants_in_response is None or len(restaurants_in_response)==0:
            break

        list_of_restaurants += restaurants_in_response
        offset += SEARCH_LIMIT
        print("Feteched {0}/{1} restuarants for cuisine {2}".format(len(list_of_restaurants),total_number_of_restauranst_possible,cuisine))
    
    return list_of_restaurants



if __name__ == '__main__':
    try:
        for cuisine in CUISINES:
            cuisine_restaurants = get_all_restaurants_of_one_cuisine(cuisine)
            with open("./restaurants/{}_data.json".format(cuisine), "w") as f:
                json.dump(cuisine_restaurants, f)
            print("{0}:{1} entries".format(cuisine, len(cuisine_restaurants)))

    except HTTPError as error:
        sys.exit(
            'Encountered HTTP error {0} on {1}:\n {2}\nAbort program.'.format(
                error.code,
                error.url,
                error.read(),
            )
        )
    
    send_data_to_dynamoDb()
    
    