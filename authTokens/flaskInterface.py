#!./test/bin/python3
### NOTE: Using Flask-Session extension to maintain SERVER-SIDE sessions. (pip install flask flask-session),(pip install python-memcached)
from flask import Flask,render_template,redirect,request,session,jsonify
from flask_session import Session
from authServer import *
from functools import wraps
from datetime import datetime

IP_ADDR = "127.0.0.1"
PORT = 3297 # 'Auth' -> numeric
AUTH_INTERFACE = AuthInterface()

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

# ONLY USE SESSIONS AS AN INTERMEDIATE STEP FOR LOGIN, SIGNUP. ONLY STORE INTERMEDIATE VALUES, CLEAR AFTER.
Session(app) # Init using server-side seesion. Note, user now sends a session cookie which is associated with a flask session.



##### UTIL
def require_session_state(state_key):
    """
    Decorator to ensure required state exists in session.
    
    Args:
        state_key: The key to check in session (e.g., 'signup_first', 'login_first')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if state_key not in session:
                print(f"[{datetime.now()}] {request.endpoint} - Session state '{state_key}' not found")
                return jsonify({"error": f"Invalid state: {state_key} not initialized"}), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def clear_session_state(*state_keys):
    """Clear specified state keys from session."""
    for key in state_keys:
        if key in session:
            del session[key]
            print(f"[{datetime.now()}] Cleared session state: {key}")



##### CONFIGURATION - INTERFACE
@app.route('/auth/signup/first', methods=['GET'])
def signup_first():
    """
    First step of signup flow: Generate and return salt for client-side hashing.
    Store salt in session state for use in signup/second.
    
    Returns:
        JSON with salt for password hashing and session identifier
    """
    try:
        print(f"[{datetime.now()}] POST /auth/signup/first - Initiating signup")
        
        # Generate salt
        result = AUTH_INTERFACE.signupFirst()
        
        # Store in session for next step
        session['signup_first'] = result
        session.modified = True
        
        print(f"[{datetime.now()}] POST /auth/signup/first - Salt generated and stored in session")
        return jsonify({
            "salt": result["salt"],
            "sessionId": request.cookies.get('session', None)
        }), 200
    
    except Exception as e:
        print(f"[{datetime.now()}] GET /auth/signup/first - ERROR: {str(e)}")
        return jsonify({"error": "Signup first step failed"}), 500


@app.route('/auth/signup/second', methods=['POST'])
@require_session_state('signup_first')
def signup_second():
    """
    Second step of signup flow: Create user and return auth token.
    Uses salt from signup/first stored in session.
    
    Expected JSON body:
        {
            "passwordHash": "...",
            "username": "...",
            "email": "..." (optional)
        }
    
    Returns:
        JSON with auth token [authHead, authTail] or error
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ['passwordHash', 'username']):
            print(f"[{datetime.now()}] POST /auth/signup/second - Missing required fields")
            return jsonify({"error": "Missing required fields: passwordHash, username"}), 400
        
        print(f"[{datetime.now()}] POST /auth/signup/second - Creating user: {data.get('username')}")
        
        # Retrieve stored state from signup/first
        first_state = session['signup_first']
        
        # Call signup second with stored state
        result = AUTH_INTERFACE.signupSecond(
            first=first_state,
            passwordHash=data['passwordHash'],
            username=data['username'],
            email=data.get('email')
        )
        
        print(result)

        if not result:
            print(f"[{datetime.now()}] POST /auth/signup/second - User creation failed for {data['username']}")
            clear_session_state('signup_first')
            return jsonify({"error": "User creation failed"}), 409
        
        print(f"[{datetime.now()}] POST /auth/signup/second - User {data['username']} created successfully, token issued")
        
        # Clear signup state after successful completion
        clear_session_state('signup_first')
        
        return jsonify({"authToken": result}), 201
    
    except Exception as e:
        print(f"[{datetime.now()}] POST /auth/signup/second - ERROR: {str(e)}")
        clear_session_state('signup_first')
        return jsonify({"error": "Signup second step failed"}), 500


# ============================================================================
# LOGIN ENDPOINTS
# ============================================================================

@app.route('/auth/login/first', methods=['POST'])
def login_first():
    """
    First step of login flow: Return salt and challenges for client-side auth.
    Store challenges and user info in session state for use in login/second.
    
    Expected JSON body:
        {
            "username": "..." OR "email": "..."
        }
    
    Returns:
        JSON with salt and challenges (uid and challenges stored in session)
    """
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        
        print(f"[{datetime.now()}] POST /auth/login/first - Lookup: username={username}, email={email}")
        
        if not username and not email:
            print(f"[{datetime.now()}] POST /auth/login/first - No username or email provided")
            return jsonify({"error": "Username or email required"}), 400
        
        result = AUTH_INTERFACE.loginFirst(username=username, email=email)
        
        if not result:
            print(f"[{datetime.now()}] POST /auth/login/first - User not found")
            return jsonify({"error": "User not found"}), 404
        
        # Store entire result in session for next step
        session['login_first'] = result
        session.modified = True
        
        print(f"[{datetime.now()}] POST /auth/login/first - Login challenge generated and stored for uid={result['uid']}")
        
        # Return salt and challenges, but keep uid in session
        return jsonify({
            "salt": result["salt"],
            "challenges": result["challenges"],
            "sessionId": request.cookies.get('session', 'new')
        }), 200
    
    except Exception as e:
        print(f"[{datetime.now()}] POST /auth/login/first - ERROR: {str(e)}")
        return jsonify({"error": "Login first step failed"}), 500


@app.route('/auth/login/second', methods=['POST'])
@require_session_state('login_first')
def login_second():
    """
    Second step of login flow: Verify credentials and return auth token.
    Uses challenges and uid from login/first stored in session.
    
    Expected JSON body:
        {
            "timestamps": [...],
            "results": [...]
        }
    
    Returns:
        JSON with auth token [authHead, authTail] or error
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ['timestamps', 'results']):
            print(f"[{datetime.now()}] POST /auth/login/second - Missing required fields")
            return jsonify({"error": "Missing required fields: timestamps, results"}), 400
        
        # Retrieve stored state from login/first
        first_state = session['login_first']
        uid = first_state['uid']
        
        print(f"[{datetime.now()}] POST /auth/login/second - Verifying credentials for uid={uid}")
        
        # Call login second with stored state
        result = AUTH_INTERFACE.loginSecond(
            first=first_state,
            timestamps=data['timestamps'],
            results=data['results']
        )
        
        if not result:
            print(f"[{datetime.now()}] POST /auth/login/second - Authentication failed for uid={uid}")
            clear_session_state('login_first')
            return jsonify({"error": "Authentication failed"}), 401
        
        print(f"[{datetime.now()}] POST /auth/login/second - Login successful for uid={uid}, token issued")
        
        # Clear login state after successful completion
        clear_session_state('login_first')
        
        return jsonify({"authToken": result}), 200
    
    except Exception as e:
        print(f"[{datetime.now()}] POST /auth/login/second - ERROR: {str(e)}")
        clear_session_state('login_first')
        return jsonify({"error": "Login second step failed"}), 500


# ============================================================================
# TOKEN AUTHENTICATION ENDPOINT
# ============================================================================

@app.route('/auth/token/verify', methods=['POST'])
def token_auth():
    """
    Single-step token authentication: Verify an existing auth token.
    
    Expected JSON body:
        {
            "authHead": "...",
            "sourceServer": "...",
            "timestamps": [...],
            "challenges": "...",
            "results": [...],
            "timeRecieveds": timestamp (optional, defaults to current time)
        }
    
    Returns:
        JSON with verification result
    """
    try:
        data = request.get_json()
        print(f"[{datetime.now()}] POST /auth/token/verify - Verifying token from {data.get('sourceServer')}")
        
        # Validate required fields
        required = ['authHead', 'sourceServer', 'timestamps', 'challenges', 'results']
        if not all(k in data for k in required):
            print(f"[{datetime.now()}] POST /auth/token/verify - Missing required fields")
            return jsonify({"error": "Missing required fields"}), 400
        
        result = AUTH_INTERFACE.tokenAuth(
            authHead=data['authHead'],
            sourceServer=data['sourceServer'],
            timestamps=data['timestamps'],
            challenges=data['challenges'],
            results=data['results'],
            timeRecieveds=data.get('timeRecieveds')
        )
        
        if not result:
            print(f"[{datetime.now()}] POST /auth/token/verify - Token verification failed")
            return jsonify({"error": "Token verification failed"}), 401
        
        print(f"[{datetime.now()}] POST /auth/token/verify - Token verified successfully")
        return jsonify({"verified": True, "result": result}), 200
    
    except Exception as e:
        print(f"[{datetime.now()}] POST /auth/token/verify - ERROR: {str(e)}")
        return jsonify({"error": "Token verification failed"}), 500


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.route('/auth/health', methods=['GET'])
def health_check():
    """Simple health check endpoint to verify service is running."""
    print(f"[{datetime.now()}] GET /auth/health - Health check")
    return jsonify({"status": "healthy", "service": "AuthService"}), 200


# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/auth/session/clear', methods=['POST'])
def clear_session():
    """Clear all auth session state (useful for aborting flows)."""
    try:
        print(f"[{datetime.now()}] POST /auth/session/clear - Clearing session state")
        clear_session_state('signup_first', 'login_first')
        session.clear()
        return jsonify({"message": "Session cleared"}), 200
    except Exception as e:
        print(f"[{datetime.now()}] POST /auth/session/clear - ERROR: {str(e)}")
        return jsonify({"error": "Failed to clear session"}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    print(f"[{datetime.now()}] 404 - Endpoint not found")
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    print(f"[{datetime.now()}] 405 - Method not allowed")
    return jsonify({"error": "Method not allowed"}), 405







if __name__ == '__main__':
    print(f"Starting AuthService on {IP_ADDR}:{PORT}")
    app.run(host=IP_ADDR, port=PORT, debug=False, threaded=False)