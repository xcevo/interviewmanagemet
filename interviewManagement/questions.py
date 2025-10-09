import os
import re
import fitz  # PyMuPDF
import json
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from werkzeug.utils import secure_filename

questions_bp = Blueprint('questions', __name__)

# Directory to save extracted images
IMAGE_SAVE_DIR = "static/images"
os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

@questions_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_questions():
    db = current_app.db
    current_admin = get_jwt_identity()

    category_id = request.form.get('category_id')
    file = request.files.get('file')

    if not category_id or not file:
        return jsonify({"error": "Category ID and file are required"}), 400

    if not ObjectId.is_valid(category_id):
        return jsonify({"error": "Invalid Category ID"}), 400

    print(f"Received upload from admin: {current_admin}")
    print(f"Category ID: {category_id}")
    print(f"File name: {file.filename}")

    # Check if category belongs to admin
    category = db.categories.find_one({
        "_id": ObjectId(category_id),
        "created_by": current_admin
    })
    if not category:
        print("Permission denied: Category does not belong to this admin.")
        return jsonify({"error": "You do not have permission to upload to this category"}), 403

    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        print(f"PDF saved to: {temp_path}")

        # Open PDF
        pdf = fitz.open(temp_path)

        # Extract text
        full_text = ""
        for page_num, page in enumerate(pdf):
            page_text = page.get_text()
            full_text += page_text
            print(f"[Page {page_num+1}] Extracted text length: {len(page_text)}")

        # Extract JSON block
        json_data_start = full_text.find('[')
        json_data_end = full_text.rfind(']')
        if json_data_start == -1 or json_data_end == -1:
            print("JSON block not found in PDF.")
            return jsonify({"error": "Could not find JSON data in PDF"}), 400

        json_str = full_text[json_data_start:json_data_end+1]

        # Fix malformed JSON (especially broken `"image":`)
        json_str_fixed = re.sub(r'"image":\s*(?=[,\}])', '"image": ""', json_str)
        json_str_fixed = re.sub(r'(?<=")(\s*\n\s*)(?=[^"]*?")', ' ', json_str_fixed)
        json_str_fixed = re.sub(r'\s+', ' ', json_str_fixed)

        try:
            questions_data = json.loads(json_str_fixed)
            print(f"✅ Parsed {len(questions_data)} questions from PDF.")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {str(e)}")
            return jsonify({"error": "JSON parsing error", "details": str(e)}), 400

        # Extract all images from all pages
        all_images = []
        for page_index in range(len(pdf)):
            images = pdf.get_page_images(page_index)
            print(f"[Page {page_index+1}] Found {len(images)} images.")
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = pdf.extract_image(xref)
                image_data = base_image["image"]
                all_images.append(image_data)

        print(f"📸 Total images extracted from PDF: {len(all_images)}")

        # Find questions that expect an image
        # Match questions that had `"image":` placeholder (converted to null)
        questions_with_images = [q for q in questions_data if q.get("image") == ""]
        print("🧩 Questions expecting images:", [q["qno"] for q in questions_with_images])

        # Extra logging for confirmation
        print("🔍 Image field value for each question:")
        for q in questions_data:
            print(f"  → q{q['qno']} image = {q.get('image')}")


        if len(all_images) < len(questions_with_images):
            return jsonify({"error": "Fewer images in PDF than required for the questions."}), 400

        # Save images and map to question numbers
        image_url_map = {}
        for i, q in enumerate(questions_with_images):
            qno = q["qno"]
            image_data = all_images[i]
            image_filename = f"q{qno}.png"
            image_path = os.path.join(IMAGE_SAVE_DIR, image_filename)
            with open(image_path, "wb") as img_file:
                img_file.write(image_data)
            image_url_map[qno] = f"/static/images/{image_filename}"
            print(f"✅ Saved image for q{qno} → {image_filename}")

        # Insert all questions into MongoDB
        inserted = []
        for q in questions_data:
            print(f"q{q['qno']} → image = {repr(q.get('image'))}")
            qno = q.get("qno")
            question_obj = {
                "qno": qno,
                "question": q.get("ques"),
                "answer": q.get("ans"),
                "difficulty": q.get("difficulty"),
                "category_id": ObjectId(category_id),
                "created_by": current_admin,
                "image_url": image_url_map.get(qno)
            }
            result = db.questions.insert_one(question_obj)
            inserted.append(str(result.inserted_id))
            print(f"🗃 Inserted question q{qno} with ID: {result.inserted_id}")

        # Cleanup
        pdf.close()
        os.remove(temp_path)
        print("🧹 Temporary file cleaned up.")

        return jsonify({
            "message": f"{len(inserted)} questions uploaded successfully.",
            "question_ids": inserted
        })

    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return jsonify({"error": "Something went wrong", "details": str(e)}), 500



@questions_bp.route('/<category_id>', methods=['GET'])
@jwt_required()
def get_questions_by_category(category_id):
    """
    Get all questions for a specific category,
    only if it belongs to the currently logged-in admin.
    """
    db = current_app.db
    current_admin = get_jwt_identity()

    # Validate the category ID
    if not ObjectId.is_valid(category_id):
        return jsonify({"error": "Invalid Category ID"}), 400

    # Ensure the category belongs to the current admin
    category = db.categories.find_one({
        "_id": ObjectId(category_id),
        "created_by": current_admin
    })

    print(category)

    if not category:
        return jsonify({"error": "Unauthorized access or category not found"}), 403

    try:
        # Get only questions created by current admin for that category
        questions = list(db.questions.find({
            "category_id": ObjectId(category_id),
            "created_by": current_admin
        }))
        print(questions)
        
        # Convert ObjectId fields to strings
        for question in questions:
            question["_id"] = str(question["_id"])
            question["category_id"] = str(question["category_id"])

        return jsonify({"questions": questions}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jwt_required()
@questions_bp.route('/test', methods=['GET'])
def test_route():
    return "Questions Blueprint is working!", 200

from flask_jwt_extended import jwt_required, get_jwt_identity

@questions_bp.route('/difficulty-count', methods=['POST'])
@jwt_required()
def get_difficulty_count():
    """
    Get the count of questions by difficulty level for a specific category,
    only if the category belongs to the logged-in admin.
    """
    db = current_app.db
    current_admin = get_jwt_identity()
    data = request.get_json()

    category_id = data.get('category_id')
    if not category_id:
        return jsonify({"error": "Category ID is required"}), 400

    if not ObjectId.is_valid(category_id):
        return jsonify({"error": "Invalid Category ID"}), 400

    # Verify the category belongs to the current admin
    category = db.categories.find_one({
        "_id": ObjectId(category_id),
        "created_by": current_admin
    })

    if not category:
        return jsonify({"error": "Unauthorized access or category not found"}), 403

    try:
        # Count questions by difficulty for this admin's category
        pipeline = [
            {
                "$match": {
                    "category": ObjectId(category_id),
                    "created_by": current_admin
                }
            },
            {
                "$group": {
                    "_id": "$difficulty",
                    "count": {"$sum": 1}
                }
            }
        ]
        results = list(db.questions.aggregate(pipeline))

        # Initialize default difficulty counts
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
        for result in results:
            difficulty = result["_id"].lower()
            if difficulty in difficulty_counts:
                difficulty_counts[difficulty] = result["count"]

        return jsonify({
            "category_id": category_id,
            "difficulty_counts": difficulty_counts
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
