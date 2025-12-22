from flask import Flask, render_template
app = Flask(__name__)

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")
    
@app.route('/inventory')
def inventory():
    return render_template("inventory.html")

@app.route('/product')
def product():
    return render_template("product.html")


@app.route('/bill')
def bill():
    return render_template("bill.html")

@app.route('/owner')
def owner():
    return render_template("owner.html")

@app.route('/navbar')
def navbar():
    return render_template("navbar.html")

if __name__ == "__main__":
    app.run(debug=True)


    