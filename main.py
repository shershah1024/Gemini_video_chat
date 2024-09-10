import os
import mimetypes
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

app = Flask(__name__)

# Configure Gemini AI
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Gemini AI model configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

chat_sessions = {}

def upload_to_gemini(file_path, mime_type):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(file_path, mime_type=mime_type)
    return file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['video']
    if video.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save the video temporarily
    temp_path = f"/tmp/{video.filename}"
    video.save(temp_path)

    # Get MIME type
    mime_type, _ = mimetypes.guess_type(temp_path)
    if not mime_type or not mime_type.startswith('video/'):
        os.remove(temp_path)
        return jsonify({'error': 'Invalid video file'}), 400

    try:
        # Upload to Gemini
        gemini_file = upload_to_gemini(temp_path, mime_type)

        # Start a new chat session
        chat_session = model.start_chat(history=[
            {
                "role": "user",
                "parts": [gemini_file],
            },
        ])

        # Store the chat session
        session_id = os.urandom(16).hex()
        chat_sessions[session_id] = chat_session

        return jsonify({'message': 'Video uploaded successfully', 'session_id': session_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        os.remove(temp_path)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id')
    message = data.get('message')

    if not session_id or not message:
        return jsonify({'error': 'Missing session_id or message'}), 400

    if session_id not in chat_sessions:
        return jsonify({'error': 'Invalid session_id'}), 400

    try:
        chat_session = chat_sessions[session_id]
        response = chat_session.send_message(message)
        return jsonify({'response': response.text}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
