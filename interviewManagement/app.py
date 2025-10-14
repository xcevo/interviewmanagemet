from flask import Flask,request,send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from categories import categories_bp
from questions import questions_bp
from users import users_bp
from auth import auth_bp
from criteria import criteria_bp
from bson import ObjectId
import json
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os


# Custom JSON Encoder for Flask
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)  # Convert ObjectId to string
        return super().default(obj)

app = Flask(__name__,static_folder='build', static_url_path='')
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

app.secret_key = 'your_secret_key'
app.config["JWT_SECRET_KEY"] = "meraSuperSecretKey123" 
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_SAMESITE"] = "Strict"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=3)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=3)
jwt = JWTManager(app)  

@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static_file(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


app.json_encoder = MongoJSONEncoder

# MongoDB configuration
MONGO_URI = "mongodb+srv://innoveotech:LPVlwcASp0OoQ8Dg@azeem.af86m.mongodb.net/InterviewDB"
DB_NAME = "InterviewDB"

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Register Blueprints
app.register_blueprint(categories_bp, url_prefix='/categories')
app.register_blueprint(questions_bp, url_prefix='/questions')
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(criteria_bp, url_prefix='/criteria')
app.register_blueprint(auth_bp, url_prefix='/auth')


# Add the MongoDB instance to the app context
@app.before_request
def attach_db():
    app.db = db
# @app.before_request
# def log_info():
#     print("🔍 Headers:", dict(request.headers))
#     print("🍪 Cookies:", request.cookies)

if __name__ == "__main__":
    app.run(debug=True)
