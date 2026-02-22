from app.extensions import mongo
from app.config import Config

def get_db():
    return mongo.db
