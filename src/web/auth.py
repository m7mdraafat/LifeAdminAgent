"""Authentication component for the web UI."""

import streamlit as st
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def init_sessions_table(repo):
    """Initialize the sessions table in the database."""
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT
        )
        """)


def init_users_table(repo):
    """Initialize the users table in the database."""
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at TEXT
        )
        """)


def create_user(repo, username: str, password: str, display_name: str = None) -> Tuple[bool, str]:
    """Create a new user account."""
    init_users_table(repo)
    
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if username exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username.lower(),))
        if cursor.fetchone():
            return False, "Username already exists"
        
        user_id = str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO users (id, username, password_hash, display_name, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            username.lower(),
            hash_password(password),
            display_name or username,
            datetime.now().isoformat()
        ))
        
        return True, user_id


def authenticate_user(repo, username: str, password: str) -> Tuple[bool, Optional[dict]]:
    """Authenticate a user and return user info if successful."""
    init_users_table(repo)
    
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, username, display_name FROM users 
        WHERE username = ? AND password_hash = ?
        """, (username.lower(), hash_password(password)))
        
        row = cursor.fetchone()
        if row:
            return True, {
                "id": row["id"],
                "username": row["username"],
                "display_name": row["display_name"]
            }
        return False, None


def create_session(repo, user_id: str) -> str:
    """Create a session token for a user."""
    init_sessions_table(repo)
    token = str(uuid.uuid4())
    
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO sessions (token, user_id, created_at)
        VALUES (?, ?, ?)
        """, (token, user_id, datetime.now().isoformat()))
    
    return token


def get_user_by_session(repo, token: str) -> Optional[dict]:
    """Get user info from session token."""
    init_users_table(repo)
    init_sessions_table(repo)
    
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT u.id, u.username, u.display_name 
        FROM users u
        JOIN sessions s ON u.id = s.user_id
        WHERE s.token = ?
        """, (token,))
        
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "username": row["username"],
                "display_name": row["display_name"]
            }
        return None


def delete_session(repo, token: str):
    """Delete a session token."""
    init_sessions_table(repo)
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))


def render_auth_page():
    """Render the login/signup page."""
    # Check for existing session token in URL
    params = st.query_params
    if "session" in params:
        token = params["session"]
        user = get_user_by_session(st.session_state.repo, token)
        if user:
            st.session_state.user = user
            st.session_state.session_token = token
            st.rerun()
    
    st.markdown(
        "<h1 style='text-align: center;'>🏠 Life Admin Assistant</h1>"
        "<p style='text-align: center; color: gray;'>Your personal life organizer</p>",
        unsafe_allow_html=True
    )
    
    st.markdown("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit:
                    if username and password:
                        success, user = authenticate_user(st.session_state.repo, username, password)
                        if success:
                            # Create session and store in URL
                            token = create_session(st.session_state.repo, user["id"])
                            st.session_state.user = user
                            st.session_state.session_token = token
                            st.query_params["session"] = token
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    else:
                        st.warning("Please enter username and password")
        
        with tab2:
            with st.form("signup_form"):
                new_username = st.text_input("Choose Username")
                new_display = st.text_input("Display Name (optional)")
                new_password = st.text_input("Choose Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                signup = st.form_submit_button("Sign Up", use_container_width=True)
                
                if signup:
                    if not new_username or not new_password:
                        st.warning("Please enter username and password")
                    elif len(new_password) < 4:
                        st.warning("Password must be at least 4 characters")
                    elif new_password != confirm_password:
                        st.error("Passwords don't match")
                    else:
                        success, result = create_user(
                            st.session_state.repo, 
                            new_username, 
                            new_password, 
                            new_display
                        )
                        if success:
                            # Auto-login after signup with session
                            user = {
                                "id": result,
                                "username": new_username.lower(),
                                "display_name": new_display or new_username
                            }
                            token = create_session(st.session_state.repo, result)
                            st.session_state.user = user
                            st.session_state.session_token = token
                            st.query_params["session"] = token
                            st.rerun()
                        else:
                            st.error(result)


def get_current_user() -> Optional[dict]:
    """Get the currently logged in user."""
    return st.session_state.get("user")


def logout():
    """Log out the current user."""
    # Delete session from database
    if "session_token" in st.session_state:
        delete_session(st.session_state.repo, st.session_state.session_token)
        del st.session_state.session_token
    # Clear URL params
    st.query_params.clear()
    # Clear session state
    if "user" in st.session_state:
        del st.session_state.user
    if "messages" in st.session_state:
        st.session_state.messages = []
    if "agent" in st.session_state:
        st.session_state.agent.reset_conversation()
