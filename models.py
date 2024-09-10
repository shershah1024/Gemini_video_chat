from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# In-memory user storage (replace with database in production)
users = {}

def get_user(user_id):
    return users.get(user_id)

def create_user(username, password):
    user_id = str(len(users) + 1)
    new_user = User(user_id, username, password)
    users[user_id] = new_user
    return new_user
