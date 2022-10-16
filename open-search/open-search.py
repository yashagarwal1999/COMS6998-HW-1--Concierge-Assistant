import json

CUISINES = ["indian", "chinese", "italian", "ethiopian", "french", "american", "mexican", "japanese", "spanish"]



if __name__ == '__main__':
    indices=[]
    restaurants = [
    for cuisine in CUISINES:
        with open('../yelp-scraper/restaurants/{}_data.json'.format(cuisine), 'r') as f:
            data = json.load(f)
            for index, restaurant in enumerate(data):
                print('{0}/{1}  restaurants of {2} cusine read'.format(index, len(data), cuisine))
                indices.append({"index": { "_index": "restaurants", "_id": restaurant.get('id') }})
                restaurants.append({ "id": restaurant.get('id'), "cuisine": cuisine})
    
    for index, restaurant in zip(indices, restaurants):
        with open('data.json', 'a') as f:
            json.dump(index, f)
            f.write("\n")
            json.dump(restaurant, f)
            f.write("\n")