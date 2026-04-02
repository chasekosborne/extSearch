#!./test/bin/python3
### NOTE: Using Flask-Session extension to maintain SERVER-SIDE sessions. (pip install flask flask-session),(pip install python-memcached)
from flask import Flask,render_template,redirect,request,session
from flask_session import Session
from authServer import *

IP_ADDR = "127.0.0.1"
PORT = 3297 # 'Auth' -> numeric
AUTH_INTERFACE = AuthInterface()

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "memcached"

# ONLY USE SESSIONS AS AN INTERMEDIATE STEP FOR LOGIN, SIGNUP. ONLY STORE INTERMEDIATE VALUES, CLEAR AFTER.
Session(app) # Init using server-side seesion. Note, user now sends a session cookie which is associated with a flask session.



##### UTIL
def clearSession():
    session["loginFirst"] = None
    session["signupFirst"] = None
###

##### CONFIGURATION






if __name__ == '__main__':
    print(f"Starting AuthService on {IP_ADDR}:{PORT}")
    app.run(host=IP_ADDR, port=PORT, debug=False, threaded=True)