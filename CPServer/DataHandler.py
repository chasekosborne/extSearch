from flask import Flask, render_template,request
from Server import CPServer
from flask_cors import CORS
import json
import os


server = CPServer()
app = Flask(__name__)
CORS(app)

@app.route('/send-data', methods=['POST'])
def receive_data():
    data = request.json
    if server.checkAuth(True,data):
        server.process_next()
        return "Valid",200
    return "Invalid",401


@app.route('/api/get-template/<template_name>', methods=['GET', 'POST'])
def get_template(template_name):
    try:
        file_path = os.path.join("templates", template_name)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
            return html_content, 200
            
    except FileNotFoundError:
        return "Template not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5001)