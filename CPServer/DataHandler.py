from flask import Flask, render_template,request
from Server import CPServer
from flask_cors import CORS
import json

server = CPServer()
app = Flask(__name__)
CORS(app)

@app.route('/send-data', methods=['POST'])
def receive_data():
    data = request.json
    server.checkAuth(True,data)
    return "Valid",200


if __name__ == '__main__':
    app.run(debug=True, port=5001)