from flask import Flask,request
from flask_cors import CORS
from pymongo import MongoClient
from categories import categories_bp
from questions import questions_bp
from users import users_bp
from auth import auth_bp
from criteria import criteria_bp
from interview import interview_bp
from bson import ObjectId
import json
from flask_jwt_extended import JWTManager
from datetime import timedelta
from voice import VOICE_BP


# Custom JSON Encoder for Flask
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)  # Convert ObjectId to string
        return super().default(obj)

app = Flask(__name__)
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
app.register_blueprint(interview_bp, url_prefix='/interview')
app.register_blueprint(VOICE_BP, url_prefix="/voice")


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
