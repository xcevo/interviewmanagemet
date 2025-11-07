# voice.py
import io, os
from datetime import datetime
from flask import Blueprint, request, send_file, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
# --- TTS clarity + meta flags (no deletion of existing lines) ---
TTS_SPEAK_META = os.getenv("TTS_SPEAK_META", "0") == "1"   # default: do NOT speak qno/difficulty
TTS_LANG = os.getenv("TTS_LANG", "en")                     # clearer en voice
TTS_TLD  = os.getenv("TTS_TLD", "com")                     # gTTS voice accent; try "us" / "co.uk" if you like
TTS_SLOW = os.getenv("TTS_SLOW", "0") == "1"               # default fast/clear

VOICE_BP = Blueprint("voice", __name__)
print("OPENAI_API_KEY present?", bool(os.getenv("OPENAI_API_KEY")))
# --- TTS options ---
# Option A: pure-Python offline (pyttsx3) -> wav; Option B: gTTS (needs internet) -> mp3
# yahan gTTS use kar rahe (simple). Install: pip install gTTS
USE_GTTS = True
try:
    from gtts import gTTS
except Exception:
    USE_GTTS = False

# --- STT options ---
# Option A: OpenAI Whisper API (env OPENAI_API_KEY) ; Option B: no-STT fallback (error)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
_openai_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        _openai_client = None


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


@VOICE_BP.route("/question-tts", methods=["GET"])
@jwt_required()
def question_tts():
    """
    Query: ?qid=<ObjectId>
    Returns: audio/mpeg (mp3) speaking the question text.
    """
    db = current_app.db
    qid = request.args.get("qid")
    if not qid:
        return jsonify({"error": "qid required"}), 400
    try:
        q = db.questions.find_one({"_id": ObjectId(qid)})
    except Exception:
        return jsonify({"error": "invalid qid"}), 400
    if not q:
        return jsonify({"error": "question not found"}), 404

    text = q.get("question") or "Question not found."
    # optionally add qno/difficulty to speech
    prefix = []
    if TTS_SPEAK_META:
        if q.get("qno"): prefix.append(f"Question {q['qno']}.")
        if q.get("difficulty"): prefix.append(f"Difficulty {q['difficulty']}.")
    speech = " ".join(prefix + [text])


    if USE_GTTS:
        mp3_bytes = io.BytesIO()
        tts = gTTS(speech, lang=TTS_LANG, tld=TTS_TLD, slow=TTS_SLOW)

        tts.write_to_fp(mp3_bytes)
        mp3_bytes.seek(0)
        return send_file(mp3_bytes, mimetype="audio/mpeg", download_name=f"q_{qid}.mp3")
    else:
        return jsonify({"error": "gTTS not available. Run: pip install gTTS"}), 500


@VOICE_BP.route("/answer-stt", methods=["POST"])
@jwt_required()
def answer_stt():
    """
    Form-Data:
      - session_id: str
      - qid: str
      - audio: file (prefer .mp3 or .wav, <= 25MB)
    Action:
      - Transcribe audio -> text
      - Save via interview session (same structure as /interview/answer)
    """
    db = current_app.db
    candidate_id = get_jwt_identity()

    sess_id = request.form.get("session_id")
    qid = request.form.get("qid")
    audio = request.files.get("audio")

    if not (sess_id and qid and audio):
        return jsonify({"error": "session_id, qid and audio are required"}), 400

    try:
        _sid = ObjectId(sess_id)
        _qid = ObjectId(qid)
    except Exception:
        return jsonify({"error": "Invalid session_id or qid"}), 400

    sess = db["interview_sessions"].find_one({"_id": _sid, "candidateId": candidate_id})
    if not sess or sess.get("status") != "ongoing":
        return jsonify({"error": "Session not found or not active"}), 404

    if not _openai_client:
        return jsonify({"error": "STT unavailable: set OPENAI_API_KEY for Whisper"}), 500

    # --- Transcribe via Whisper ---
    # Accept mp3/wav/etc. Read into memory and send
    file_bytes = audio.read()
    fname = audio.filename or "audio.wav"

    try:
        # Whisper transcription
        transcript = _openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=(fname, file_bytes)
        )
        text = transcript.text.strip()
    except Exception as e:
        return jsonify({"error": f"Transcription failed: {e}"}), 500

    # --- Save answer like /interview/answer ---
    answers = sess.get("answers", [])
    found = False
    for a in answers:
        if a.get("qid") == qid:
            a["answer_text"] = text
            a["at"] = _now_iso()
            found = True
            break
    if not found:
        answers.append({"qid": qid, "answer_text": text, "at": _now_iso()})

    db["interview_sessions"].update_one({"_id": _sid}, {"$set": {"answers": answers}})
    return jsonify({"message": "Saved (voice)", "transcript": text, "session_id": sess_id, "qid": qid}), 200
