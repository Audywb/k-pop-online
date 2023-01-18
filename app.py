from flask import Flask, render_template, redirect, request, url_for, flash, session, jsonify, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename

import os
import bcrypt

app = Flask(__name__)
app.secret_key = "KpopShop.com"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

client = MongoClient('localhost', 27017)
db = client.kpop_db
users = db.users
products = db.products
carts = db.carts
purchased = db.purchased

UPLOAD_FOLDER = "/Users/66987/Documents/work-project/k-pop-shop/static/product-images"
ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg", "gif"]


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "name" not in session:
            warning = "กรุณาเข้าสู่ระบบ"
            # Auth required
            return render_template('login.html', warning=warning)
        else:
            return function()
    wrapper.__name__ = function.__name__
    return wrapper

def login_is_required_admin(function):
    def wrapper(*args, **kwargs):
        if "name" not in session:
            warning = "กรุณาเข้าสู่ระบบ"
            # Auth required
            return render_template('login.html', warning=warning)
        elif session['is_admin'] != True:
            warning = "กรุณาเข้าสู่ระบบ ด้วยบัญชีผู้ดูแลระบบ"
            return render_template('login.html', warning=warning)
        else:
            return function()
    wrapper.__name__ = function.__name__
    return wrapper


@app.route("/")
def index():
    cout_cart = 0
    all_product = products.find()
    username = False
    if "name" in session:
        username = session['name']
        cout_cart = carts.count_documents({"user_email": session['email']})
    return render_template('index.html', username=username, product=all_product, cout_cart=cout_cart)

@app.post("/search/<category>")
def search(category):
    print(category)
    cout_cart = 0
    all_product = products.find({"category": category})
    username = False
    if "name" in session:
        username = session['name']
        cout_cart = carts.count_documents({"user_email": session['email']})
    if category == "ALL":
        all_product = products.find()
    return render_template('category.html', username=username, product=all_product, cout_cart=cout_cart)


@app.route("/upload/product", methods=['POST', 'GET'])
def upload_product():
    if 'file' not in request.files:
        return jsonify({'error': 'image not provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'no file selected'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        print("filename", filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        product_name = request.form['name']
        price = request.form['price']
        stock = request.form['stock']
        category = request.form['select']
        image = filename
        products.insert_one({
            'name': product_name,
            'price': price,
            'stock': stock,
            'category': category,
            'image': image
        })
        flash('เพิ่มสินค้าสำเร็จ')

    return redirect(url_for('admin'))


@app.post('/addToCart/<id>/')
def addToCart(id):
    if request.method == 'POST':
        user_email = session['email']
        user_name = session['name']
        product = products.find_one({"_id": ObjectId(id)})
        carts.insert_one(
            {
                'user_name': user_name,
                'user_email': user_email,
                'product_id': id,
                'product_name': product['name'],
                'product_price': product['price'],
                'product_stock': product['stock'],
                'product_amount': 1,
                'product_image': product['image']
            })

    return redirect(url_for('index'))


@app.post('/update/amount/<id>/')
def updateAmountCart(id):
    if request.method == 'POST':
        amount = request.form['amount']
        carts.find_one_and_update({"_id": ObjectId(id)}, {
            "$set": {'product_amount': int(amount)}})

    return redirect(url_for('view_cart'))

@app.post('/add/purchased/<payment>/')
def addPurchased(payment):
    print(request.form['optradio'])
    pay_by = request.form['optradio']
    if bool(payment) == True:
        product = carts.find({"user_email": session['email']})
        purchased.insert_many(product)
        carts.delete_many({"user_email": session['email']})

    return redirect(url_for('paymented'))


@app.route("/paymented")
@login_is_required
def paymented():
    product = []
    product = purchased.find({"user_email": session['email']})
    flash('ชำระเงินเสร็จสิ้น')
    return render_template('paymented.html', product=product)


@app.route("/cart/payment")
@login_is_required
def payment():
    product = []
    cout_cart = carts.count_documents({"user_email": session['email']})
    if cout_cart > 0:
        product = carts.find({"user_email": session['email']})
        price_total = []
        price = 0
        address = session['address']
        phone = session['phone_number']
        name = session['name']
        for i in carts.find({"user_email": session['email']}):
            total = i['product_price']
            n = i['product_amount']
            totaled = int(total)*int(n)
            price_total.append(int(totaled))
        price = sum(price_total)
    else:
        flash('ยังไม่ได้เพิ่มสินค้า')
    return render_template('payment.html', cout_cart=cout_cart, cart_product=product, price_total=price, address=address, phone=phone, name=name)


@app.route("/cart/view")
@login_is_required
def view_cart():
    product = []
    price = 0
    address = "1234"
    cout_cart = carts.count_documents({"user_email": session['email']})
    if cout_cart > 0:
        product = carts.find({"user_email": session['email']})
        price_total = []
        address = session['address']
        for i in carts.find({"user_email": session['email']}):
            total = i['product_price']*i['product_amount']
            price_total.append(int(total))
        price = sum(price_total)
        print(price)
    else:
        flash('ยังไม่ได้เพิ่มสินค้า')
    return render_template('cart.html', cout_cart=cout_cart, cart_product=product, price_total=price, address=address)


@app.post('/delete/item/<id>/')
def deleteItem(id):
    if "name" in session:
        carts.delete_one({"_id": ObjectId(id)})
        return redirect(url_for('view_cart'))
    else:
        return abort(404)


@app.post('/delete/item/db/<id>/')
def deleteItem_to_Product(id):
    if "name" in session:
        products.delete_one({"_id": ObjectId(id)})
        return redirect(url_for('viewAdminItem'))
    else:
        return abort(404)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        signin_user = users.find_one({"email": request.form['email']})
        if signin_user:
            password = signin_user['password']
            if bcrypt.hashpw(request.form['password'].encode('utf-8'), password) == password:
                session['name'] = signin_user['name']
                session['is_admin'] = signin_user['is_admin']
                session['email'] = request.form['email']
                session['address'] = signin_user['address']
                session['phone_number'] = signin_user['phone_number']
                if session['is_admin'] == True:
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('index'))
            else:
                warning = "รหัสผ่านไม่ถูกต้อง"
                return render_template('login.html', warning=warning)
        else:
            warning = "อีเมลไม่ถูกต้อง"
            return render_template('login.html', warning=warning)
    return render_template('login.html')


@app.route("/register", methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone_number = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(14))
        is_admin = False
        users.insert_one(
            {
                'name': name,
                'address': address,
                'phone_number': phone_number,
                'email': email,
                'password': hashed,
                'is_admin': is_admin
            })
        message = "สมัครสมาชิกสำเร็จ"
        return render_template('register.html', message=message)

    return render_template('register.html')


@app.route("/about_me")
@login_is_required
def about_me():
    cout_cart = carts.count_documents({"user_email": session['email']})
    username = session['name']
    mydata = users.find_one({"name": username})
    return render_template('about.html', username=username, mydata=mydata, cout_cart=cout_cart)


@app.route("/setting")
def setting():
    if "name" in session:
        username = session['name']
    else:
        username = 'not_login'
    return render_template('setting.html', username=username)


@app.route("/admin", methods=['POST', 'GET'])
@login_is_required_admin
def admin():
    return render_template('admin.html', username="username")


@app.route("/admin/view")
@login_is_required_admin
def viewAdminItem():
    username = session['name']
    all_product = products.find()
    return render_template('all_view_admin.html', username=username, product=all_product)


@app.route('/logout')
def logout():
    session.pop('name', None)
    session.pop('is_admin', None)
    session.pop('email', None)
    session.pop('address', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8000)
