from flask import Blueprint, request, jsonify, current_app,make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity,set_refresh_cookies

auth_bp = Blueprint('auth', __name__)

# Register a new admin
@auth_bp.route('/register', methods=['POST'])
def register_admin():
    data = request.get_json()
    username = data.gfromet('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    db = current_app.db
    existing_admin = db.admin.find_one({'username': username})

    if existing_admin:
        return jsonify({'error': 'Admin already exists'}), 409

    hashed_password = generate_password_hash(password)
    db.admin.insert_one({
        'username': username,
        'password': hashed_password
    })

    return jsonify({'message': 'Admin registered successfully'}), 201

# Admin login
@auth_bp.route('/login', methods=['POST'])
def login_admin():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    db = current_app.db
    admin = db.admin.find_one({'username': username})

    if not admin or not check_password_hash(admin['password'], password):
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=str(admin['username']))
    refresh_token = create_refresh_token(identity=str(admin['username']))

    response = make_response(jsonify({
        'access_token': access_token,
        'message': 'Login successful'
    }))
    set_refresh_cookies(response, refresh_token)
    # Set refresh token in HttpOnly cookie
    response.set_cookie(
            'refresh_token',
            value=refresh_token,
            httponly=True,         # 🔐 Prevent JS access
            secure=True,           # 🔐 Send over HTTPS only (not in dev)
            samesite='Strict',     # 🔐 Or 'Lax' if you need cross-site login
            path='/auth/refresh'
        )
    return response


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True, locations=["cookies"])
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    response = jsonify({
        'access_token': access_token,
        'message': 'Access token refreshed successfully'
    })
    return response

# Example of a protected route (optional)
@auth_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected_route():
    current_user = get_jwt_identity()
    return jsonify({'message': f'Hello Admin {current_user}, you are authenticated!'}), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = jsonify({'message': 'Logged out'})
    response.delete_cookie('refresh_token', path='/auth/refresh')
    return response



@auth_bp.route('/can/login', methods=['POST'])
def candidate_login():
    try:
        # 1️⃣ Read request data
        data = request.get_json()
        candidate_id = data.get('candidateId')
        password = data.get('password')

        if not candidate_id or not password:
            return jsonify({"error": "candidateId and password are required"}), 400

        # 2️⃣ DB collections
        db = current_app.db
        user_collection = db["users scheduler"]
        criteria_collection = db["criteria"]

        # 3️⃣ Find candidate
        candidate = user_collection.find_one({"candidateId": candidate_id})
        if not candidate or candidate.get("password") != password:
            return jsonify({"error": "Invalid credentials"}), 401

        # 4️⃣ Generate JWT tokens
        access_token = create_access_token(identity=candidate_id)
        refresh_token = create_refresh_token(identity=candidate_id)

        # 5️⃣ Enrich interview data with criteria info
        interviews_data = []

        for interview in candidate.get("interviews", []):
            interview_name = interview.get("interview_name")

            criteria = criteria_collection.find_one(
                {"name": interview_name},
                {"_id": 0, "time": 1, "valid_from": 1, "valid_to": 1}
            )

            interviews_data.append({
                "interview_name": interview_name,
                "time": criteria.get("time") if criteria else None,
                "valid_from": criteria.get("valid_from") if criteria else None,
                "valid_to": criteria.get("valid_to") if criteria else None
            })

        # 6️⃣ Prepare response
        response = make_response(jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "candidate": {
                "candidateId": candidate["candidateId"],
                "name": candidate.get("name"),
                "email": candidate.get("email"),
                "phone": candidate.get("phone"),
                "interviews": interviews_data
            }
        }))

        # 7️⃣ Set refresh token in HttpOnly cookie
        response.set_cookie(
            'refresh_token',
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite='Strict',
            path='/auth/refresh'
        )

        return response, 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500