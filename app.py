from flask import Blueprint, request, render_template, redirect, url_for , session , Flask, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db , User , Product , Inventory , Sale , SaleItem
from sqlalchemy import func
from datetime import datetime, timedelta
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

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

    

@app.route('/test_post', methods=['GET', 'POST'])
def test_post():
    if request.method == 'POST':
        print("=" * 50)
        print("TEST POST REQUEST RECEIVED")
        print("Method:", request.method)
        print("Form data:", dict(request.form))
        print("=" * 50)
        return jsonify({"status": "success", "message": "POST request received", "data": dict(request.form)})
    return '''
    <form method="POST" action="/test_post">
        <input type="text" name="test" value="test_value">
        <button type="submit">Test POST</button>
    </form>
    '''

@app.route('/dashboard')
def dashboard():
    products = Product.query.all()
    
    # Stats
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Total Sales Today
    daily_sales = db.session.query(func.sum(Sale.total_amount)).filter(func.date(Sale.created_at) == today).scalar() or 0
    
    # Total Bills Today
    daily_bills = Sale.query.filter(func.date(Sale.created_at) == today).count()
    
    # Cash / UPI Sales
    cash_sales = db.session.query(func.sum(Sale.total_amount)).filter(func.date(Sale.created_at) == today, Sale.payment_mode == 'Cash').scalar() or 0
    upi_sales = db.session.query(func.sum(Sale.total_amount)).filter(func.date(Sale.created_at) == today, Sale.payment_mode == 'UPI').scalar() or 0
    
    # Low Stock Items (< 10 quantity)
    low_stock = Inventory.query.filter(Inventory.quantity < 5).count()
    
    # Recent Bills
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()
    
    # Chart Data (Last 7 Days)
    dates = []
    amounts = []
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).date()
        date_str = date.strftime('%Y-%m-%d')
        # SQLite doesn't have a nice date function, so we filter by range or iterating.
        # Simple iterator for small app:
        day_total = db.session.query(func.sum(Sale.total_amount)).filter(func.date(Sale.created_at) == date_str).scalar() or 0
        dates.append(date.strftime('%d %b'))
        amounts.append(day_total)
    
    chart_data = {
        'labels': dates,
        'data': amounts
    }
    
    # Sales Overview (Today)
    # Total Items Sold Today
    items_sold_today = db.session.query(func.sum(SaleItem.quantity)).join(Sale).filter(func.date(Sale.created_at) == today).scalar() or 0
    
    # Average Bill Value Today
    avg_bill_value = int(daily_sales / daily_bills) if daily_bills > 0 else 0
    
    # Inventory Status (join Product and Inventory)
    # inventory_status = db.session.query(Product, Inventory).join(Inventory, Product.product_id == Inventory.product_id).all()
    # Actually, let's just use Inventory.query and access .product (backref)
    inventory_items = Inventory.query.join(Product).all()

    # Profit Metrics (Today)
    daily_profit = db.session.query(
        func.sum(SaleItem.quantity * Product.profit)
    ).join(Sale, SaleItem.sale_id == Sale.sale_id
    ).join(Product, SaleItem.product_id == Product.product_id
    ).filter(func.date(Sale.created_at) == today).scalar() or 0
    
    profit_margin = int((daily_profit / daily_sales * 100)) if daily_sales > 0 else 0

    return render_template("dashboard.html", products=products, daily_sales=daily_sales, daily_bills=daily_bills, low_stock=low_stock, recent_sales=recent_sales, inventory_items=inventory_items, cash_sales=cash_sales, upi_sales=upi_sales, items_sold_today=items_sold_today, avg_bill_value=avg_bill_value, chart_data=chart_data, daily_profit=daily_profit, profit_margin=profit_margin)


@app.route('/create_sale', methods=['POST'])
def create_sale():
    print("=" * 50)
    print("CREATE SALE REQUEST RECEIVED")
    data = request.get_json()
    print("Data:", data)
    
    try:
        payment_mode = data.get('payment_mode', 'Cash')
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'message': 'No items in sale'})
            
        total_amount = 0
        new_sale = Sale(total_amount=0, payment_mode=payment_mode)
        db.session.add(new_sale)
        db.session.flush() # get ID
        
        processed_items = []
        
        for item in items:
            pid = int(item['product_id'])
            qty = int(item['quantity'])
            
            product = Product.query.get(pid)
            inventory = Inventory.query.filter_by(product_id=pid).first()
            
            if not product:
                raise Exception(f"Product ID {pid} not found")
            
            if not inventory:
                # Auto-create inventory if missing (optional, but good for safety)
                # Or raise error. Let's raise error as stock should exist.
                # For this specific user request "make everything working", maybe better to be robust. 
                # But logic says if not in inventory, can't sell.
                raise Exception(f"No inventory record for {product.product_name}")
                
            if inventory.quantity < qty:
                raise Exception(f"Insufficient stock for {product.product_name}. Available: {inventory.quantity}")
                
            # Calculate price
            price = product.rate * qty
            total_amount += price
            
            # Deduct stock
            inventory.quantity -= qty
            
            # Create SaleItem
            sale_item = SaleItem(
                sale_id=new_sale.sale_id,
                product_id=pid,
                inventory_id=inventory.inventory_id,
                quantity=qty,
                price=price
            )
            db.session.add(sale_item)
            
        new_sale.total_amount = total_amount
        db.session.commit()
        
        return jsonify({'success': True, 'sale_id': new_sale.sale_id})
        
    except Exception as e:
        db.session.rollback()
        print("Error creating sale:", e)
        return jsonify({'success': False, 'message': str(e)})
    
@app.route('/add_product', methods=['POST'])
def add_product():
    print("=" * 50)
    print("POST REQUEST RECEIVED at /add_product")
    print("Request method:", request.method)
    print("Form data:", request.form)
    print("=" * 50)
    
    product_name = request.form.get('product_name')
    rate = request.form.get('rate')
    unit = request.form.get('unit')
    profit = request.form.get('profit')
    
    print(f"Product Name: {product_name}")
    print(f"Rate: {rate}")
    print(f"Unit: {unit}")
    print(f"Profit: {profit}")
    
    if not product_name or not rate or not unit:
        flash('Please fill all required fields', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        new_product = Product(
            product_name=product_name,
            rate=float(rate),
            unit=unit,
            profit=float(profit) if profit else 0.0
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        print("Product added successfully!")
    except Exception as e:
        db.session.rollback()
        flash('Error adding product: ' + str(e), 'error')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('dashboard'))

@app.route('/inventory')
def inventory():
    products = Product.query.all()
    inventory_items = Inventory.query.join(Product).all()
    return render_template("inventory.html", products=products, inventory_items=inventory_items)

@app.route('/update_inventory', methods=['POST'])
def update_inventory():
    print("=" * 50)
    print("POST REQUEST RECEIVED at /update_inventory")
    print("Request method:", request.method)
    print("Form data:", request.form)
    print("=" * 50)
    
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    
    print(f"Product ID: {product_id}")
    print(f"Quantity: {quantity}")
    
    if not product_id or not quantity:
        flash('Please select product and enter quantity', 'error')
        return redirect(url_for('inventory'))
    
    try:
        # Check if inventory already exists for this product
        existing_inventory = Inventory.query.filter_by(product_id=product_id).first()
        
        if existing_inventory:
            existing_inventory.quantity = int(quantity)
            print("Updated existing inventory")
        else:
            new_inventory = Inventory(
                product_id=int(product_id),
                quantity=int(quantity)
            )
            db.session.add(new_inventory)
            print("Created new inventory")
        
        db.session.commit()
        flash('Inventory updated successfully!', 'success')
        print("Inventory updated successfully!")
    except Exception as e:
        db.session.rollback()
        flash('Error updating inventory: ' + str(e), 'error')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('inventory'))

@app.route('/generate_bill', methods=['POST'])
def generate_bill():
    print("=" * 50)
    print("POST REQUEST RECEIVED at /generate_bill")
    print("Request method:", request.method)
    print("Form data:", request.form)
    print("=" * 50)
    
    inventory_id = request.form.get('inventory_id')
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    rate = request.form.get('rate')
    
    print(f"Inventory ID: {inventory_id}")
    print(f"Product ID: {product_id}")
    print(f"Quantity: {quantity}")
    print(f"Rate: {rate}")
    
    if not inventory_id or not product_id or not quantity or not rate:
        flash('Missing required information', 'error')
        return redirect(url_for('inventory'))
    
    try:
        # Get product details
        product = Product.query.get(product_id)
        inventory = Inventory.query.get(inventory_id)
        
        if not product or not inventory:
            flash('Product or inventory not found', 'error')
            return redirect(url_for('inventory'))
        
        # Calculate total price
        qty = int(quantity)
        price_per_unit = float(rate)
        total_price = qty * price_per_unit
        
        # Create sale
        new_sale = Sale(total_amount=float(total_price))
        db.session.add(new_sale)
        db.session.flush()  # Get the sale_id
        
        # Create sale item
        sale_item = SaleItem(
            sale_id=new_sale.sale_id,
            product_id=int(product_id),
            inventory_id=int(inventory_id),
            quantity=qty,
            price=float(total_price)
        )
        db.session.add(sale_item)
        
        # Update inventory quantity
        inventory.quantity -= qty
        if inventory.quantity < 0:
            inventory.quantity = 0
        
        db.session.commit()
        
        # Redirect to bill page with sale_id
        return redirect(url_for('bill', sale_id=new_sale.sale_id))
    except Exception as e:
        db.session.rollback()
        flash('Error generating bill: ' + str(e), 'error')
        return redirect(url_for('inventory'))

@app.route('/product')
def product():
    products = Product.query.all()
    return render_template("product.html", products=products)

@app.route('/update_product', methods=['POST'])
def update_product():
    print("=" * 50)
    print("POST REQUEST RECEIVED at /update_product")
    print("Form data:", request.form)
    print("=" * 50)
    
    product_id = request.form.get('product_id')
    product_name = request.form.get('product_name')
    rate = request.form.get('rate')
    unit = request.form.get('unit')
    profit = request.form.get('profit')
    
    if not product_name or not rate or not unit:
        flash('Please fill all required fields', 'error')
        return redirect(url_for('product'))
    
    try:
        if product_id:  # Update existing product
            product = Product.query.get(product_id)
            if product:
                product.product_name = product_name
                product.rate = float(rate)
                product.unit = unit
                product.profit = float(profit) if profit else 0.0
                flash('Product updated successfully!', 'success')
                print("Product updated successfully!")
            else:
                flash('Product not found', 'error')
        else:  # Add new product
            new_product = Product(
                product_name=product_name,
                rate=float(rate),
                unit=unit,
                profit=float(profit) if profit else 0.0
            )
            db.session.add(new_product)
            flash('Product added successfully!', 'success')
            print("Product added successfully!")
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('Error saving product: ' + str(e), 'error')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('product'))

@app.route('/delete_product', methods=['POST'])
def delete_product():
    print("=" * 50)
    print("POST REQUEST RECEIVED at /delete_product")
    print("Form data:", request.form)
    print("=" * 50)
    
    product_id = request.form.get('product_id')
    
    if not product_id:
        flash('Product ID is required', 'error')
        return redirect(url_for('product'))
    
    try:
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
            db.session.commit()
            flash('Product deleted successfully!', 'success')
            print("Product deleted successfully!")
        else:
            flash('Product not found', 'error')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product: ' + str(e), 'error')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('product'))


@app.route('/bill')
def bill():
    sale_id = request.args.get('sale_id')
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    if sale_id:
        # Show specific bill
        sale = Sale.query.get(sale_id)
        if sale:
            sale_items = SaleItem.query.filter_by(sale_id=sale_id).all()
            return render_template("bill.html", sale=sale, sale_items=sale_items, current_date=current_date)
            
    # Show All Bills (History)
    all_sales = Sale.query.order_by(Sale.created_at.desc()).all()
    return render_template("bill.html", all_sales=all_sales, current_date=current_date)

@app.route('/owner')
def owner():
    return render_template("owner.html")

@app.route('/navbar')
def navbar():
    return render_template("navbar.html")

# Add before_request handler to log all requests
@app.before_request
def log_request_info():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.path}")
    if request.method == 'POST':
        print(f"POST Data: {dict(request.form)}")
    print("-" * 50)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Flask App Starting...")
    print("Available Routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} [{', '.join(rule.methods)}]")
    print("=" * 50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)


    