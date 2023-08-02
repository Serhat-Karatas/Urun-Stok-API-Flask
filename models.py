from datetime import datetime

from sqlalchemy.orm import relationship

from __init__ import db


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    category = relationship("Category", backref="products")       #bir kategoriye ait tüm ürünlere kategori_objesi.products şeklinde erişilebilir.


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))

    parent = relationship("Category", remote_side=[id], backref="children")


class Token(db.Model):
    __tablename__ = 'token_table'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'))
    user = relationship("UserTable")


class UserTable(db.Model):
    __tablename__ = 'user_table'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    def check_password(self, password):
        if self.password == password:
            return True
        else:
            return False

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'password': self.password,
            'is_admin': self.is_admin
        }



class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer)
    order_date = db.Column(db.DateTime)
    total_price = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id if self.user_id else None,
            'user_name': UserTable.query.with_entities(UserTable.name).filter_by(id=self.user_id).scalar() if self.user_id else None,
            'product_id': self.product_id if self.product_id else None,
            'product_name': Product.query.with_entities(Product.name).filter_by(id=self.product_id).scalar() if self.product_id else None,
            'quantity': self.quantity,
            'order_date': self.order_date,
            'total_price': self.total_price
        }

