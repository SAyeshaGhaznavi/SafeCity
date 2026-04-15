from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/portal')
def portal():
    return render_template('portal.html')

@app.route('/report')
def report():
    return render_template('report.html')

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)