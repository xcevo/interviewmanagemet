from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
from flask_jwt_extended import jwt_required, get_jwt_identity

categories_bp = Blueprint('categories', __name__)

# GET all categories created by current admin
@categories_bp.route('/', methods=['GET'])
@jwt_required()
def get_categories():
    db = current_app.db
    current_username = get_jwt_identity()
    categories = list(db.categories.find({"created_by": current_username}))
    
    for category in categories:
        category['_id'] = str(category['_id'])

    return jsonify(categories), 200

# CREATE category, assigning to current admin
@categories_bp.route('/', methods=['POST'])
@jwt_required()
def create_category():
    db = current_app.db
    data = request.json
    current_username = get_jwt_identity()

    if not data.get('name'):
        return jsonify({"error": "Category name is required"}), 400

    category_data = {
        "name": data["name"],
        "created_by": current_username
    }

    result = db.categories.insert_one(category_data)
    return jsonify({"message": "Category created", "id": str(result.inserted_id)}), 201

# UPDATE only if category belongs to current admin
@categories_bp.route('/<category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    db = current_app.db
    data = request.json
    current_username = get_jwt_identity()   

    try:
        result = db.categories.update_one(
            {"_id": ObjectId(category_id), "created_by": current_username},
            {"$set": data}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Category not found or unauthorized"}), 404
        return jsonify({"message": "Category updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# DELETE only if category belongs to current admin
@categories_bp.route('/<category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    db = current_app.db
    current_username = get_jwt_identity()

    try:
        result = db.categories.delete_one({
            "_id": ObjectId(category_id),
            "created_by": current_username
        })
        if result.deleted_count == 0:
            return jsonify({"error": "Category not found or unauthorized"}), 404
        return jsonify({"message": "Category deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

