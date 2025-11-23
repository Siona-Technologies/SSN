import uuid
import time

class AuthSession:
    def __init__(self, user_id, device_id):
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id
        self.device_id = device_id
        self.created_at = time.time()
        self.is_active = True

class AuthManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, user_id, device_id):
        session = AuthSession(user_id, device_id)
        self.sessions[session.session_id] = session
        return session

    def validate_session(self, session_id):
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return False
        return True

    def end_session(self, session_id):
        session = self.sessions.get(session_id)
        if session:
            session.is_active = False
