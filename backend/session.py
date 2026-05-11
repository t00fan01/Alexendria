sessions = {}

def get_session_history(session_id):
    return sessions.get(session_id, [])

def add_to_session(session_id, question, answer):
    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append({"question": question, "answer": answer})