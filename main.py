from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/what-is-fit')
def what_is_fit():
    return render_template('what-is-fit.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/fit')
def fit():
    return render_template('fit.html')


@app.route('/solution')
def solution():
    return render_template('solution.html')

@app.route('/login')
def login():
    return render_template('login.html')
    
@app.route('/guest')
def guest():
    return render_template('guest.html')
    
if __name__ == '__main__':
    app.run(debug=True)