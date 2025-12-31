from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ===================== USERS =====================
class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)


# ===================== PRODUCTS =====================
class Product(db.Model):
    __tablename__ = 'products'

    product_id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(200), nullable=False)
    rate = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(50), nullable=False)  # kg / litre / pcs

    inventory = db.relationship(
        'Inventory',
        backref='product',
        uselist=False,
        cascade='all, delete-orphan'
    )


# ===================== INVENTORY =====================
class Inventory(db.Model):
    __tablename__ = 'inventory'

    inventory_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.product_id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )
    quantity = db.Column(db.Integer, nullable=False)

    sales = db.relationship(
        'SaleItem',
        backref='inventory',
        cascade='all, delete-orphan'
    )


# ===================== SALES =====================
class Sale(db.Model):
    __tablename__ = 'sales'

    sale_id = db.Column(db.Integer, primary_key=True)
    total_amount = db.Column(db.Integer, nullable=False)

    items = db.relationship(
        'SaleItem',
        backref='sale',
        cascade='all, delete-orphan'
    )


# ===================== SALE ITEMS =====================
class SaleItem(db.Model):
    __tablename__ = 'sale_items'

    item_id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(
        db.Integer,
        db.ForeignKey('sales.sale_id', ondelete='CASCADE'),
        nullable=False
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.product_id', ondelete='CASCADE'),
        nullable=False
    )
    inventory_id = db.Column(
        db.Integer,
        db.ForeignKey('inventory.inventory_id', ondelete='CASCADE'),
        nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)

    product = db.relationship('Product')
