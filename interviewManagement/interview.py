# interview.py
import os, time, math, random
from datetime import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

# ==== OpenAI client (minimal dependency, env-driven) ====
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception:
    _openai_client = None

interview_bp = Blueprint("interview", __name__)
SESSIONS = "interview_sessions"

def _now_iso():
    return datetime.utcnow().isoformat() + "Z"

def _require_openai():
    if not _openai_client:
        raise RuntimeError("OPENAI_API_KEY missing or OpenAI client not available")

# ---------- Utility: fetch criteria + questions ----------
def _load_criteria_and_questions(db, interview_name):
    # criteria by name (admin-independent; if multiple, pick latest)
    crit = db.criteria.find_one({"name": interview_name})
    if not crit:
        return None, []

    cat_id = crit.get("category")
    if not isinstance(cat_id, ObjectId):
        try:
            cat_id = ObjectId(cat_id)
        except Exception:
            return crit, []

    # counts
    easy_n = int(crit.get("easy", 0) or 0)
    med_n  = int(crit.get("medium", 0) or 0)
    hard_n = int(crit.get("hard", 0) or 0)

    # Pull questions by difficulty from this category_id
    def pick(dif, n):
        if n <= 0:
            return []
        cur = db.questions.find({"category_id": cat_id, "difficulty": dif})
        arr = list(cur)
        random.shuffle(arr)
        return arr[:n]

    qs = pick("easy", easy_n) + pick("medium", med_n) + pick("hard", hard_n)

    # shape down to safe payload (no correct answers here)
    safe_qs = []
    for q in qs:
        safe_qs.append({
            "qid": str(q["_id"]),
            "qno": q.get("qno"),
            "question": q.get("question"),
            "difficulty": q.get("difficulty"),
            "image_url": q.get("image_url")
        })
    return crit, safe_qs

# ---------- Route: start interview ----------
@interview_bp.route("/start", methods=["POST"])
@jwt_required()
def start_interview():
    """
    Body: { "interview_name": "DSA Round-1" }
    Returns: { session_id, interview_name, time, passing_marks, questions: [...] }
    """
    db = current_app.db
    candidate_id = get_jwt_identity()
    data = request.get_json() or {}
    interview_name = str(data.get("interview_name", "")).strip()
    if not interview_name:
        return jsonify({"error": "interview_name is required"}), 400

    # Verify this interview is assigned to this candidate
    user = db["users scheduler"].find_one({"candidateId": candidate_id})
    if not user:
        return jsonify({"error": "Candidate not found"}), 404

    assigned = user.get("interviews", [])
    if not any(i.get("interview_name") == interview_name for i in assigned):
        return jsonify({"error": "Interview not assigned to this candidate"}), 403

    crit, safe_questions = _load_criteria_and_questions(db, interview_name)
    if not crit or not safe_questions:
        return jsonify({"error": "No criteria/questions found for this interview"}), 404

    # Create a session doc
    sess = {
        "candidateId": candidate_id,
        "interview_name": interview_name,
        "criteria_id": str(crit["_id"]),
        "status": "ongoing",
        "created_at": _now_iso(),
        "answers": [],       # list of {qid, answer_text, at}
        "questions": safe_questions  # freeze served questions
    }
    ins = db[SESSIONS].insert_one(sess)

    return jsonify({
        "session_id": str(ins.inserted_id),
        "interview_name": interview_name,
        "time": crit.get("time"),                 # as created in criteria
        "passing_marks": crit.get("passing_marks"),
        "questions": safe_questions
    }), 200

# ---------- Route: answer one question ----------
@interview_bp.route("/answer", methods=["POST"])
@jwt_required()
def submit_answer():
    """
    Body: { "session_id": "...", "qid": "...", "answer_text": "..." }
    Upserts/updates the candidate's answer for that qid in the session doc.
    """
    db = current_app.db
    candidate_id = get_jwt_identity()
    data = request.get_json() or {}

    sess_id = data.get("session_id")
    qid     = data.get("qid")
    atext   = (data.get("answer_text") or "").strip()

    if not sess_id or not qid:
        return jsonify({"error": "session_id and qid are required"}), 400
    try:
        _sid = ObjectId(sess_id)
        _qid = ObjectId(qid)
    except Exception:
        return jsonify({"error": "Invalid session_id or qid"}), 400

    sess = db[SESSIONS].find_one({"_id": _sid, "candidateId": candidate_id})
    if not sess or sess.get("status") != "ongoing":
        return jsonify({"error": "Session not found or not active"}), 404

    # add or replace answer
    answers = sess.get("answers", [])
    found = False
    for a in answers:
        if a.get("qid") == qid:
            a["answer_text"] = atext
            a["at"] = _now_iso()
            found = True
            break
    if not found:
        answers.append({"qid": qid, "answer_text": atext, "at": _now_iso()})

    db[SESSIONS].update_one({"_id": _sid}, {"$set": {"answers": answers}})
    return jsonify({"message": "Saved", "session_id": sess_id, "qid": qid}), 200

# ---------- LLM Scoring ----------
_SCORING_SYSTEM_PROMPT = (
    "You are an impartial technical examiner. "
    "Given a reference answer and a candidate's answer, return a JSON object with:\n"
    '{"score": <0-100 integer>, "justification": "<one short sentence>"}.\n'
    "Score on semantic correctness, coverage of key points, and clarity; be strict but fair. "
    "If the candidate answer is empty or unrelated, score near 0."
)

def _score_with_openai(reference: str, candidate: str) -> dict:
    _require_openai()
    prompt = (
        f"Reference answer:\n{reference}\n\n"
        f"Candidate answer:\n{candidate}\n\n"
        "Respond ONLY with the JSON."
    )
    # Using Responses API (modern SDK). Fallback to Chat Completions if needed.
    try:
        resp = _openai_client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": _SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        text = resp.output_text
    except Exception:
        # try chat.completions for compatibility
        chat = _openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        text = chat.choices[0].message.content

    # naive JSON parse
    import json
    try:
        out = json.loads(text.strip())
        sc = int(max(0, min(100, int(out.get("score", 0)))))
        just = str(out.get("justification", "")).strip()
        return {"score": sc, "justification": just}
    except Exception:
        return {"score": 0, "justification": "Malformed model output"}

# ---------- Route: finish + evaluate ----------
@interview_bp.route("/finish", methods=["POST"])
@jwt_required()
def finish_interview():
    """
    Body: { "session_id": "..." }
    Evaluates all answered questions vs DB 'answer', computes totals, marks session finished.
    """
    db = current_app.db
    candidate_id = get_jwt_identity()
    data = request.get_json() or {}
    sess_id = data.get("session_id")
    if not sess_id:
        return jsonify({"error": "session_id is required"}), 400
    try:
        _sid = ObjectId(sess_id)
    except Exception:
        return jsonify({"error": "Invalid session_id"}), 400

    sess = db[SESSIONS].find_one({"_id": _sid, "candidateId": candidate_id})
    if not sess or sess.get("status") != "ongoing":
        return jsonify({"error": "Session not found or already finished"}), 404

    # Load criteria (time/passing marks)
    crit = db.criteria.find_one({"_id": ObjectId(sess["criteria_id"])})
    passing_marks = int(crit.get("passing_marks", 0)) if crit else 0

    # Build map of ground-truth answers
    qids = [ObjectId(a["qid"]) for a in sess.get("answers", []) if "qid" in a]
    qmap = {}
    if qids:
        for q in db.questions.find({"_id": {"$in": qids}}):
            qmap[str(q["_id"])] = {
                "answer": q.get("answer") or "",
                "question": q.get("question") or "",
                "difficulty": q.get("difficulty")
            }

    # Evaluate each answered question
    results = []
    total_score = 0
    for a in sess.get("answers", []):
        qid = a["qid"]
        cand = a.get("answer_text", "")
        ref = (qmap.get(qid) or {}).get("answer", "")
        if not ref:
            # If no reference in DB, give neutral 0 and move on
            res = {"qid": qid, "score": 0, "justification": "Reference missing"}
        else:
            res = _score_with_openai(ref, cand)
            res["qid"] = qid
        total_score += int(res["score"])
        results.append(res)

    # Normalize to 100 based on #answered (simple average)
    answered = max(1, len(results))
    overall = round(total_score / answered)

    status = "pass" if overall >= passing_marks else "fail"

    db[SESSIONS].update_one(
        {"_id": _sid},
        {"$set": {
            "status": "finished",
            "finished_at": _now_iso(),
            "evaluation": {
                "per_question": results,
                "overall": overall,
                "passing_marks": passing_marks,
                "status": status
            }
        }}
    )

    # Return compact result for app UI
    return jsonify({
        "session_id": sess_id,
        "overall": overall,
        "passing_marks": passing_marks,
        "status": status,
        "per_question": results
    }), 200
