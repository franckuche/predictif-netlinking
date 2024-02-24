from pymongo import MongoClient

class MongoDB:
    def __init__(self, uri, db_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def insert_user(self, user_data):
        users_collection = self.db['users']
        return users_collection.insert_one(user_data).inserted_id

    def find_user(self, query):
        users_collection = self.db['users']
        return users_collection.find_one(query)