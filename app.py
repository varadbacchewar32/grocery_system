from flask import Blueprint, request, render_template, redirect, url_for , session , Flask
from werkzeug.security import generate_password_hash, check_password_hash
from models import db , User , Product , Inventory , Sale , SaleItem
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grocery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.secret_key = 'secret_key'
db.init_app(app)
with app.app_context():
    db.create_all()

    # check if admin already exists
    admin = User.query.filter_by(username='admin').first()

    if not admin:
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created successfully")
    else:
        print("Admin user already exists")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            return render_template("login.html", error="Invalid username or password")

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


    