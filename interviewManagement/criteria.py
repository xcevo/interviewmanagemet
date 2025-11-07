from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
from flask_jwt_extended import jwt_required, get_jwt_identity

criteria_bp = Blueprint('criteria', __name__)

# ---- tiny helper: basic YYYY-MM-DD check (keep strings in DB) ----
def _norm_date(s):
    if not s:
        return None
    if isinstance(s, str) and len(s) == 10:
        try:
            y, m, d = s.split('-')
        except ValueError:
            return None
        if y.isdigit() and m.isdigit() and d.isdigit():
            return f"{y.zfill(4)}-{m.zfill(2)}-{d.zfill(2)}"
    return None


# GET: fetch only criteria created by current admin
@criteria_bp.route('/', methods=['GET'])
@jwt_required()
def get_criteria():
    db = current_app.db
    current_admin = get_jwt_identity()

    criteria = list(db.criteria.find({"created_by": current_admin}))
    for criterion in criteria:
        criterion['_id'] = str(criterion['_id'])

        # expand category reference if it's an ObjectId
        if 'category' in criterion and isinstance(criterion['category'], ObjectId):
            category = db.categories.find_one({
                "_id": criterion['category'],
                "created_by": current_admin  # Confirm ownership
            })
            if category:
                criterion['category'] = {
                    'id': str(category['_id']),
                    'name': category['name']
                }
            else:
                criterion['category'] = None  # Or a default value

        # validity fields will already be stored as strings; just ensure str
        if 'valid_from' in criterion and criterion['valid_from'] is not None:
            criterion['valid_from'] = str(criterion['valid_from'])
        if 'valid_to' in criterion and criterion['valid_to'] is not None:
            criterion['valid_to'] = str(criterion['valid_to'])

    return jsonify(criteria), 200


# POST: create criteria only with current admin’s category
@criteria_bp.route('/', methods=['POST'])
@jwt_required()
def create_criteria():
    db = current_app.db
    current_admin = get_jwt_identity()
    data = request.json or {}

    # Validate input (keep existing semantics)
    if not data.get('name') or not data.get('category') or not data.get('time') or not data.get('passing_marks'):
        return jsonify({"error": "Interview name, category, time, and passing marks are required"}), 400

    # Validate and verify category ownership
    try:
        category_id = ObjectId(data['category'])
    except Exception:
        return jsonify({"error": "Invalid category ID"}), 400

    category = db.categories.find_one({
        "_id": category_id,
        "created_by": current_admin
    })
    if not category:
        return jsonify({"error": "You can only use your own categories"}), 403

    # Ensure unique name per admin
    if db.criteria.find_one({"name": data['name'], "created_by": current_admin}):
        return jsonify({"error": "You already have a criteria with this name"}), 400

    # ---- NEW: validity (optional) ----
    vf = _norm_date(data.get('valid_from'))
    vt = _norm_date(data.get('valid_to'))
    if (data.get('valid_from') and not vf) or (data.get('valid_to') and not vt):
        return jsonify({"error": "valid_from/valid_to must be YYYY-MM-DD"}), 400
    if vf and vt and vt < vf:
        return jsonify({"error": "valid_to cannot be before valid_from"}), 400

    payload = {
        "name": data['name'],
        "category": category_id,
        "easy": data.get('easy', 0),
        "medium": data.get('medium', 0),
        "hard": data.get('hard', 0),
        "time": data['time'],
        "passing_marks": data['passing_marks'],
        "created_by": current_admin
    }
    if vf is not None:
        payload["valid_from"] = vf
    if vt is not None:
        payload["valid_to"] = vt

    result = db.criteria.insert_one(payload)
    return jsonify({"message": "Interview criteria created", "id": str(result.inserted_id)}), 201


# PUT: update only if current admin is the owner
@criteria_bp.route('/<criteria_id>', methods=['PUT'])
@jwt_required()
def update_criteria(criteria_id):
    db = current_app.db
    current_admin = get_jwt_identity()
    data = request.json or {}

    try:
        # Check if the criteria belongs to the current admin
        existing = db.criteria.find_one({
            "_id": ObjectId(criteria_id),
            "created_by": current_admin
        })
        if not existing:
            return jsonify({"error": "Criteria not found or unauthorized"}), 404

        # If category is being updated, validate ownership
        if 'category' in data:
            try:
                category_id = ObjectId(data['category'])
            except Exception:
                return jsonify({"error": "Invalid category ID format"}), 400

            category = db.categories.find_one({
                "_id": category_id,
                "created_by": current_admin
            })
            if not category:
                return jsonify({"error": "You can only assign your own categories"}), 403

            # Replace with validated ObjectId
            data['category'] = category_id

        # ---- NEW: validity normalization/guards on update ----
        update_fields = dict(data)
        if 'valid_from' in data:
            vf = _norm_date(data.get('valid_from'))
            if data.get('valid_from') and not vf:
                return jsonify({"error": "valid_from must be YYYY-MM-DD"}), 400
            update_fields['valid_from'] = vf
        if 'valid_to' in data:
            vt = _norm_date(data.get('valid_to'))
            if data.get('valid_to') and not vt:
                return jsonify({"error": "valid_to must be YYYY-MM-DD"}), 400
            update_fields['valid_to'] = vt

        # If both present in this request, cross-check order
        if 'valid_from' in update_fields and 'valid_to' in update_fields:
            if update_fields.get('valid_from') and update_fields.get('valid_to'):
                if update_fields['valid_to'] < update_fields['valid_from']:
                    return jsonify({"error": "valid_to cannot be before valid_from"}), 400

        # Perform the update
        db.criteria.update_one(
            {"_id": ObjectId(criteria_id), "created_by": current_admin},
            {"$set": update_fields}
        )

        return jsonify({"message": "Criteria updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# DELETE: only delete if owned by current admin
@criteria_bp.route('/<criteria_id>', methods=['DELETE'])
@jwt_required()
def delete_criteria(criteria_id):
    db = current_app.db
    current_admin = get_jwt_identity()

    try:
        result = db.criteria.delete_one({
            "_id": ObjectId(criteria_id),
            "created_by": current_admin
        })
        if result.deleted_count == 0:
            return jsonify({"error": "Criteria not found or unauthorized"}), 404
        return jsonify({"message": "Criteria deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# POST: fetch questions for a criteria (owned by current admin)
@criteria_bp.route('/questions', methods=['POST'])
@jwt_required()
def get_questions_by_interview_name():
    db = current_app.db
    current_admin = get_jwt_identity()
    data = request.json or {}

    interview_name = data.get('name')
    if not interview_name:
        return jsonify({"error": "Interview name is required"}), 400

    # Find criteria created by current admin
    criteria = db.criteria.find_one({
        "name": interview_name,
        "created_by": current_admin
    })
    if not criteria:
        return jsonify({"error": "Criteria not found or unauthorized"}), 404

    try:
        category_id = ObjectId(criteria['category'])
    except Exception:
        return jsonify({"error": "Invalid category reference"}), 400

    easy_count = criteria.get('easy', 0)
    medium_count = criteria.get('medium', 0)
    hard_count = criteria.get('hard', 0)

    # Fetch questions by category and difficulty
    easy_questions = list(db.questions.find({"category": category_id, "difficulty": "easy"}))[:easy_count]
    medium_questions = list(db.questions.find({"category": category_id, "difficulty": "medium"}))[:medium_count]
    hard_questions = list(db.questions.find({"category": category_id, "difficulty": "hard"}))[:hard_count]

    all_questions = []
    for q in easy_questions + medium_questions + hard_questions:
        q['_id'] = str(q['_id'])
        for key, value in q.items():
            if isinstance(value, ObjectId):
                q[key] = str(value)
        all_questions.append(q)

    return jsonify({
        "questions": all_questions,
        "message": f"Fetched {len(all_questions)} questions"
    }), 200


