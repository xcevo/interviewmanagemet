from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import pandas as pd
import tempfile
import os
import secrets

users_bp = Blueprint('users', __name__)
COLLECTION_NAME = "users scheduler"


def generate_password(length=8):
    """Generate a random password (plain text)."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@users_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    current_admin = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            temp_file_path = temp_file.name
            file.save(temp_file_path)

        data = pd.read_excel(temp_file_path)

        required_columns = ["candidateId", "name", "email", "phone", "interview_name", "interview_date", "interview_time"]
        if not all(col in data.columns for col in required_columns):
            os.remove(temp_file_path)
            return jsonify({"error": f"File must contain columns: {', '.join(required_columns)}"}), 400

        db = current_app.db
        collection = db[COLLECTION_NAME]
        upserted_ids = []

        # Group by candidateId for multiple rows of same user in same file
        grouped = data.groupby("candidateId")

        for candidate_id, group in grouped:
            candidate_id = str(candidate_id).strip()

            # Build list of interviews for this candidate
            interviews = []
            for _, row in group.iterrows():
                interviews.append({
                    "interview_name": str(row["interview_name"]),
                    "interview_date": str(row["interview_date"]),
                    "interview_time": str(row["interview_time"])
                })

            # Pick first row for user info
            first_row = group.iloc[0]

            existing_user = collection.find_one({"candidateId": candidate_id, "uploaded_by": current_admin})

            if existing_user:
                # Append new interviews (avoid duplicates by comparing dicts)
                existing_interviews = existing_user.get("interviews", [])
                for interview in interviews:
                    if interview not in existing_interviews:
                        existing_interviews.append(interview)

                collection.update_one(
                    {"candidateId": candidate_id, "uploaded_by": current_admin},
                    {"$set": {"interviews": existing_interviews}}
                )
            else:
                # New user → generate password
                user_doc = {
                    "candidateId": candidate_id,
                    "name": str(first_row["name"]),
                    "email": str(first_row["email"]),
                    "phone": str(first_row["phone"]),
                    "uploaded_by": current_admin,
                    "password": generate_password(),
                    "interviews": interviews
                }
                collection.insert_one(user_doc)

            upserted_ids.append(candidate_id)

        os.remove(temp_file_path)

        return jsonify({
            "message": "Users successfully processed",
            "candidate_ids": upserted_ids
        }), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@users_bp.route('/get-all-candidates', methods=['GET'])
@jwt_required()
def get_all_candidates():
    try:
        current_admin = get_jwt_identity()
        db = current_app.db
        collection = db[COLLECTION_NAME]

        candidates = list(collection.find(
            {"uploaded_by": current_admin},
            {"_id": 0}
        ))

        return jsonify({
            "count": len(candidates),
            "candidates": candidates
        }), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500



@users_bp.route('/candidate/<candidate_id>', methods=['GET'])
@jwt_required()
def get_candidate(candidate_id):
    current_admin = get_jwt_identity()
    db = current_app.db
    collection = db[COLLECTION_NAME]

    candidate = collection.find_one(
        {"candidateId": candidate_id, "uploaded_by": current_admin},
        {"_id": 0}
    )

    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    return jsonify(candidate), 200


@users_bp.route('/candidate/<candidate_id>', methods=['PUT'])
@jwt_required()
def update_candidate(candidate_id):
    current_admin = get_jwt_identity()
    db = current_app.db
    collection = db[COLLECTION_NAME]
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    result = collection.update_one(
        {"candidateId": candidate_id, "uploaded_by": current_admin},
        {"$set": data}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Candidate not found or unauthorized"}), 404

    return jsonify({"message": "Candidate updated successfully"}), 200


@users_bp.route('/candidate/<candidate_id>', methods=['DELETE'])
@jwt_required()
def delete_candidate(candidate_id):
    current_admin = get_jwt_identity()
    db = current_app.db
    collection = db[COLLECTION_NAME]

    result = collection.delete_one({
        "candidateId": candidate_id,
        "uploaded_by": current_admin
    })

    if result.deleted_count == 0:
        return jsonify({"error": "Candidate not found or unauthorized"}), 404

    return jsonify({"message": "Candidate deleted successfully"}), 200





@users_bp.route('/get-user-topics', methods=['POST'])
def get_user_topics():
    try:
        # Parse request JSON
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({"error": "Missing 'user_id' in request"}), 400

        user_id = data['user_id']

        # Query the MongoDB collection for the given user_id
        db = current_app.db  # Access the MongoDB instance from the current app context
        user_topics = list(db[COLLECTION_NAME].find({"candidateId": user_id}, {"_id": 0}))

        if not user_topics:
            return jsonify({"message": "No topics found for the given user_id"}), 404

        return jsonify({
            "user_id": user_id,
            "topics": user_topics
        }), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    

DEADLINE = datetime(2025, 10, 2)   # YYYY, MM, DD


@users_bp.route('/update-interview', methods=['POST'])
@jwt_required()
def update_interview():
    try:
        if datetime.now() > DEADLINE:
            return jsonify({"error": "Interview update period has expired"}), 403

        # ✅ FIX: now this will return candidateId string
        candidate_id = get_jwt_identity()

        data = request.get_json()
        if not data or "interview_name" not in data or "new_date" not in data or "new_time" not in data:
            return jsonify({"error": "Fields required: interview_name, new_date, new_time"}), 400

        interview_name = str(data["interview_name"]).strip()
        new_date = str(data["new_date"]).strip()
        new_time = str(data["new_time"]).strip()

        db = current_app.db
        collection = db["users scheduler"]

        candidate = collection.find_one({"candidateId": candidate_id})
        if not candidate:
            return jsonify({"error": "Candidate not found"}), 404

        updated = False
        interviews = candidate.get("interviews", [])

        for interview in interviews:
            if interview.get("interview_name") == interview_name:
                interview["interview_date"] = new_date
                interview["interview_time"] = new_time
                updated = True
                break

        if not updated:
            return jsonify({"error": "Interview not found"}), 404

        collection.update_one(
            {"candidateId": candidate_id},
            {"$set": {"interviews": interviews}}
        )

        return jsonify({
            "message": "Interview updated successfully",
            "updated_interview": {
                "interview_name": interview_name,
                "interview_date": new_date,
                "interview_time": new_time
            }
        }), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
