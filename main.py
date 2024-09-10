import os
import mimetypes
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True)
    videos = db.relationship('Video', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('ChatMessage', backref='chat_session', lazy=True, cascade='all, delete-orphan')
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    chat_sessions = db.relationship('ChatSession', backref='video', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def upload_to_gemini(file_path, mime_type):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(file_path, mime_type=mime_type)
    return file

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))
        
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registered successfully')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_video():
    video_id = request.form.get('video_id')
    
    if video_id:
        # Starting a new chat session for an existing video
        video = Video.query.get(video_id)
        if not video or video.user_id != current_user.id:
            return jsonify({'error': 'Invalid video ID'}), 400
        
        temp_path = f"/tmp/{video.filename}"
        mime_type = video.mime_type
    elif 'video' in request.files:
        # Uploading a new video
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
        
        # Save video information to the database
        new_video = Video(user_id=current_user.id, filename=video.filename, mime_type=mime_type)
        db.session.add(new_video)
        db.session.commit()
        video_id = new_video.id
    else:
        return jsonify({'error': 'No video file or video ID provided'}), 400

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
        db_chat_session = ChatSession(user_id=current_user.id, session_id=session_id, video_id=video_id)
        db.session.add(db_chat_session)
        db.session.commit()

        return jsonify({'message': 'Chat session started successfully', 'session_id': session_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file if it was a new upload
        if 'video' in request.files:
            os.remove(temp_path)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    session_id = data.get('session_id')
    message = data.get('message')

    if not session_id or not message:
        return jsonify({'error': 'Missing session_id or message'}), 400

    chat_session = ChatSession.query.filter_by(user_id=current_user.id, session_id=session_id).first()
    if not chat_session:
        return jsonify({'error': 'Invalid session_id'}), 400

    try:
        # Recreate the chat history from the database
        chat_history = [
            {"role": msg.role, "parts": [msg.content]}
            for msg in ChatMessage.query.filter_by(chat_session_id=chat_session.id).order_by(ChatMessage.timestamp)
        ]

        # Recreate the Gemini chat session
        gemini_chat = model.start_chat(history=chat_history)

        # Send the new message
        response = gemini_chat.send_message(message)

        # Save the user message and AI response to the database
        user_message = ChatMessage(chat_session_id=chat_session.id, role="user", content=message)
        ai_message = ChatMessage(chat_session_id=chat_session.id, role="model", content=response.text)
        db.session.add(user_message)
        db.session.add(ai_message)
        db.session.commit()

        return jsonify({'response': response.text}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_sessions')
@login_required
def get_sessions():
    sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    return jsonify([
        {
            'id': session.id,
            'session_id': session.session_id,
            'created_at': session.created_at.isoformat(),
            'video_filename': session.video.filename
        }
        for session in sessions
    ])

@app.route('/get_session_messages/<session_id>')
@login_required
def get_session_messages(session_id):
    chat_session = ChatSession.query.filter_by(user_id=current_user.id, session_id=session_id).first()
    if not chat_session:
        return jsonify({'error': 'Invalid session_id'}), 400

    messages = ChatMessage.query.filter_by(chat_session_id=chat_session.id).order_by(ChatMessage.timestamp).all()
    return jsonify([
        {
            'role': message.role,
            'content': message.content,
            'timestamp': message.timestamp.isoformat()
        }
        for message in messages
    ])

@app.route('/video_gallery')
@login_required
def video_gallery():
    videos = Video.query.filter_by(user_id=current_user.id).order_by(Video.upload_date.desc()).all()
    return render_template('video_gallery.html', videos=videos)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
