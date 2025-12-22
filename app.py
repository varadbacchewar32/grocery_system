from flask import Flask

app = Flask(__name__)

@app.route('/home')
def hello():
    a=0
    return 1/a

if __name__ == "__main__":
    app.run(debug=True)


    