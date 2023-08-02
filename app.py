from flask_cors import CORS
from models import *
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from initialize_db import createApp, createDB
from flask import request, jsonify
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime




app = createApp()
CORS(app)
createDB()
app.config['SECRET_KEY'] = 'mysecretkey'
jwt = JWTManager(app)


def delete_category(category):
    # Alt kategorileri sil
    for child in category.children:
        delete_category(child)

    # Kategoriye ait ürünleri deaktive et
    deactivate_products(category.products)

    # Kategoriyi sil
    db.session.delete(category)


def deactivate_products(products):
    for product in products:
        product.category_id = None
        product.is_active = False
        db.session.add(product)


def get_products_by_category(category):
    products = []
    if not category.children:
        products = category.products
    else:
        for child in category.children:
            products.extend(get_products_by_category(child))
    return products


@app.route('/category/<int:category_id>/products', methods=['GET'])
def get_product_by_category(category_id):            #seçilen kategoriye ait tüm ürünleri döndürür.
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'message': 'Kategori bulunamadı'}), 404

    product_list = get_products_by_category(category)

    products = []
    for product in product_list:
        products.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'stock': product.stock,
            'description': product.description
        })

    return jsonify({'products': products}), 200


@app.route('/category/<int:category_id>', methods=['DELETE'])
def delete_category_api(category_id):
    user = get_user_by_token()
    if user.is_admin:
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'message': 'Kategori bulunamadı'}), 404

        delete_category(category)
        db.session.commit()

        return jsonify({'message': 'Kategori başarıyla silindi'}), 200

    return jsonify({'message': 'Yetkisiz erişim'}), 200


@app.route('/login', methods=['POST'])       
def login():      # kullanıcı kimlik bilgileriyle oturum açmayı sağlar
    content = request.json
    password, email = content["password"], content["email"]
    user = UserTable.query.filter_by(email=email).first()   # Veritabanında kullanıcı arama
    if user is None or not user.check_password(password):   # E-posta veya parola yanlış ise hata yanıtı döndür
        return jsonify({'status': 'false', 'description': 'Email or Password Wrong'})
    # JWT oluşturma
    expires = datetime.timedelta(1.0)      # 24 saat sürecek bir zaman aralığı nesnesi oluşturur
    token = create_access_token(identity=email, expires_delta=expires)
    # Token veritabanında kaydedilir veya güncellenir
    token_record = Token.query.filter_by(user_id=user.id).first()
    if token_record is None:
        token_record = Token(token=token, user_id=user.id)
        db.session.add(token_record)
    else:
        token_record.token = token
    db.session.commit()

    return jsonify({'token': token, 'status': 'true', 'description': 'Login Successfully', 'is_admin': user.is_admin})

@app.route('/logout', methods=['GET'])
@jwt_required()
def logout():
    try:
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split()[1]
        else:
            return jsonify({'error': 'Token not found'}), 401
        token_obj = Token.query.filter_by(token=token).first()
        db.session.delete(token_obj)
        db.session.commit()
        return jsonify({'status': 'true', 'description': 'Logout Successfully'}), 200
    except Exception as e:
        print("Veritabanı hatası:", e), 500



@app.route('/reset_password', methods=['POST'])
def reset_password():                         # Bu api şuan çalışmaz. Doğru smtp sağlayıcı bilgileri verilirse çalışıyor.
    email = request.json['email']
    user = UserTable.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Geçersiz e-posta adresi'}), 404
    print(user)
    print(email)
    # Şifre sıfırlama token'ını oluşturma
    token = generate_password_token(email)
    print(token)
    login = "example@examplemailprovider"     # Mail gönderme işlemi yapacağın posta ismi.
    recipients_emails = email
    subject = 'Parola yenile'
    header = 'Merhaba, parolanızı sıfırlamak için aşağıdaki bağlantıya tıklayın'
    body = '<a class="btn btn-primary" href="https://google.com/{}" role="button">TIKLA</a>'.format(token)   # Parola yenileme sayfasına yönlendir.
    print(body)
    msg = MIMEMultipart('alternative')

    html_content = '''
    <html>
        <head>
            <style>
                h2 {{
                    margin: 0;
                    padding: 20px;
                    color: #ffffff;
                    background: #4b9fc5;
                }}
                .btn {{
                    display: block;
                    width: 100%;
                    background-color: #4b9fc5;
                    color: #ffffff;
                    text-decoration: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    text-align: center;
                }}
                .btn:hover {{
                    background-color: #3579a8;
                }}
            </style>
        </head>
        <body>
            <h2>{}</h2>
            <br>
            {}
        </body>
    </html>
    '''.format(header, body)

    part = MIMEText(html_content, 'html')

    msg.attach(part)

    msg['Subject'] = subject
    msg['From'] = login
    msg['To'] = recipients_emails

    smtp_host = 'smtp.example.com'      # SMTP saglayıcını yaz.
    smtp_port = 587
    password = "parola"              # Gönderme işlemi yapacağın mailin parolasını yaz.

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(login, password)
        server.send_message(msg)
        print("Mail başarıyla gönderildi.")

    return jsonify({'message': 'Şifre sıfırlama e-postası gönderildi'}), 200


@app.route('/reset_password/<token>', methods=['POST'])
def reset_password_confirm(token):
    email = verify_password_token(token)
    if not email:
        return jsonify({'message': 'Geçersiz veya süresi dolmuş token'}), 400

    new_password = request.json['new_password']
    user = UserTable.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Geçersiz e-posta adresi'}), 404

    user.password = new_password
    db.session.commit()

    return jsonify({'message': 'Parola başarıyla güncellendi'}), 200


def generate_password_token(email):
    serializer = URLSafeTimedSerializer('mysecretkey')  
    token = serializer.dumps(email)

    return token



# Token'ı doğrulama işlemini gerçekleştiren fonksiyon
def verify_password_token(token):
    serializer = URLSafeTimedSerializer('mysecretkey')  

    try:
        email = serializer.loads(token)
        return email
    except:
        return None



@app.route('/get_all_orders', methods=['GET'])
def get_all_orders():
    user = get_user_by_token()
    if user and user.is_admin:
        orders = Order.query.all()
        order_list = [order.to_dict() for order in orders]
        return order_list

    return jsonify("Yetkisiz erişim!")



@app.route('/get_all_by_user_mail/<int:user_id>', methods=['GET'])
def get_orders_by_userid(user_id):
    user = get_user_by_token()
    if user and user.is_admin:
        orders = Order.query.filter_by(user_id=user_id).all()
        if not orders:
            return jsonify("Hiç sipariş yok.")
        order_list = [order.to_dict() for order in orders]
        return order_list

    return jsonify("Yetkisiz erişim!")



def get_user_by_token():
    try:
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split()[1]
        else:
            return None
        user = Token.query.filter_by(token=token).first().user
        return user if user else None
    except Exception as e:
        print("Veritabanı hatası:", e), 500
        return None


@app.route('/my_orders', methods=['GET'])
def my_orders():
    user = get_user_by_token()
    if user:
        orders = Order.query.filter_by(user_id=user.id).all()
        if not orders:
            return jsonify("Hiç sipariş yok.")
        order_list = [order.to_dict() for order in orders]
        return order_list
    return jsonify({'message': 'Token not found'}), 200


@app.route('/root-categories', methods=['GET'])
def get_root_categories():
    categories = Category.query.filter(Category.parent_id.is_(None)).all()
    category_list = []
    for category in categories:
        category_data = {
            'id': category.id,
            'name': category.name
        }
        category_list.append(category_data)
    return jsonify(category_list)


@app.route('/get-all-products', methods=['GET'])
def get_all_products():
    products = Product.query.all()
    product_list = []
    for product in products:
        product_dict = {
            'id': product.id,
            'name': product.name,
            'category_id': product.category_id,
            'price': product.price,
            'stock': product.stock,
            'description': product.description,
            'is_active': product.is_active
        }
        product_list.append(product_dict)

    return jsonify({'products': product_list})


@app.route('/buy_products', methods=['POST'])
def buy_products():
    user = get_user_by_token()
    if user:
        try:
            orders = request.json
            for order in orders:
                product_id = order.get('product_id')
                quantity = order.get('quantity')

                product = Product.query.get(product_id)
                if not product:
                    return jsonify({'message': f'Ürün bulunamadı: {product_id}'}), 404

                if product.stock < quantity:
                    return jsonify({'message': f'Yetersiz stok: {product.name}'}), 400

                total_price = product.price * quantity

                new_order = Order(
                    user_id=user.id,
                    product_id=product_id,
                    quantity=quantity,
                    order_date=datetime.datetime.now(),
                    total_price=total_price
                )
                db.session.add(new_order)

                product.stock -= quantity

            db.session.commit()

            return jsonify({'message': 'Siparişler başarıyla kaydedildi.'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'Token not found'}), 200


@app.route('/add_product', methods=['POST'])
def add_product():
    user = get_user_by_token()
    if user and user.is_admin:
        data = request.get_json()

        name = data.get('name')
        category_id = data.get('category_id')
        price = data.get('price')
        stock = data.get('stock')
        description = data.get('description')
        is_active = data.get('is_active', True)

        new_product = Product(
            name=name,
            category_id=category_id,
            price=price,
            stock=stock,
            description=description,
            is_active=is_active
        )
        db.session.add(new_product)
        db.session.commit()

        return jsonify({'message': 'Ürün başarıyla eklendi'}), 200

    return jsonify({'message': 'Yetkisiz erişim'}), 200


@app.route('/update_product/<int:product_id>', methods=['POST'])
def update_product(product_id):
    user = get_user_by_token()
    if user and user.is_admin:
        data = request.get_json()

        product = Product.query.get(product_id)
        if not product:
            return jsonify({'message': 'Ürün bulunamadı'}), 404

        name = data.get('name')
        category_id = data.get('category_id')
        price = data.get('price')
        stock = data.get('stock')
        description = data.get('description')
        is_active = data.get('is_active')


        product.name = name if name else product.name
        product.category_id = category_id if category_id else product.category_id
        product.price = price if price else product.price
        product.stock = stock if stock else product.stock
        product.description = description if description else product.description
        product.is_active = is_active if is_active is not None else product.is_active

        db.session.commit()

        return jsonify({'message': 'Ürün başarıyla güncellendi'}), 200

    return jsonify({'message': 'Yetkisiz erişim'}), 200


@app.route('/add_categories', methods=['POST'])
def create_category():
    user = get_user_by_token()
    if user and user.is_admin:
        data = request.json
        name = data.get('name')
        parent_id = data.get('parent_id')

        new_category = Category(name=name, parent_id=parent_id)
        db.session.add(new_category)
        db.session.commit()

        return jsonify({'message': 'Kategori başarıyla oluşturuldu'}), 201

    return jsonify({'message': 'Yetkisiz erişim'}), 200





@app.route('/get-child-categories', methods=['POST'])
def get_child_categories():        # Sadece bir alt kategorileri alır.
    parent_id = request.json['parent']
    child_categories = Category.query.filter_by(parent_id=parent_id).all()
    child_list = []
    for category in child_categories:
        category_dict = {
            'id': category.id,
            'name': category.name,
            'category_id': category.parent_id
        }
        child_list.append(category_dict)

    return jsonify({'child categories': child_list})


@app.route('/delete-products/<int:product_id>', methods=['GET'])
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Ürün bulunamadı.'}), 404

    product.is_active = False
    db.session.commit()

    return jsonify({'message': 'Ürün başarıyla silindi.'})


if __name__ == "__main__":
    app.run()
