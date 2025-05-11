import requests
from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Order counter and reset tracking
order_counter = 0
last_reset_time = datetime.now()

# Database structure with unit added
grocery_data = {
    "categories": [
        {
            "id": 1,
            "name": "Grains & Cereals",
            "subcategories": [
                {
                    "id": 101,
                    "name": "Rice",
                    "products": [
                        {"id": 1001, "name": "Basmati Rice", "price": 80, "available": True, "unit": "1 kg"},
                        {"id": 1002, "name": "Brown Rice", "price": 70, "available": True, "unit": "1 kg"}
                    ]
                },
                {
                    "id": 102,
                    "name": "Flour",
                    "products": [
                        {"id": 1003, "name": "Wheat Flour", "price": 30, "available": True, "unit": "1 kg"},
                        {"id": 1004, "name": "Gram Flour", "price": 40, "available": True, "unit": "500 g"}
                    ]
                }
            ]
        },
        {
            "id": 2,
            "name": "Oil & Ghee",
            "subcategories": [
                {
                    "id": 201,
                    "name": "Cooking Oil",
                    "products": [
                        {"id": 2001, "name": "Sunflower Oil", "price": 120, "available": True, "unit": "1 L"},
                        {"id": 2002, "name": "Mustard Oil", "price": 110, "available": True, "unit": "1 L"}
                    ]
                }
            ]
        }
    ]
}

# Helper functions
def find_category(category_id):
    return next((c for c in grocery_data["categories"] if c["id"] == category_id), None)

def find_subcategory(category_id, subcategory_id):
    category = find_category(category_id)
    if category:
        return next((s for s in category["subcategories"] if s["id"] == subcategory_id), None)
    return None

def find_product(category_id, subcategory_id, product_id):
    subcategory = find_subcategory(category_id, subcategory_id)
    if subcategory:
        return next((p for p in subcategory["products"] if p["id"] == product_id), None)
    return None

def generate_id(existing_ids):
    return max(existing_ids) + 1 if existing_ids else 1

def get_order_number():
    global order_counter, last_reset_time

    # Check if 24 hours have passed since last reset
    if datetime.now() - last_reset_time >= timedelta(hours=24):
        order_counter = 0
        last_reset_time = datetime.now()

    order_counter += 1
    return order_counter

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html', grocery_data=grocery_data, show_whatsapp=False)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()

    if not name or not phone or not address:
        return redirect(url_for('index'))

    selected_items = []
    total = 0

    for category in grocery_data["categories"]:
        for subcategory in category["subcategories"]:
            for product in subcategory["products"]:
                quantity = request.form.get(f'product_{product["id"]}', '0')
                try:
                    quantity = int(quantity)
                    if quantity > 0:
                        selected_items.append({
                            'name': product['name'],
                            'quantity': quantity,
                            'price': product['price'],
                            'unit': product.get('unit', '1 pc'),
                            'subtotal': quantity * product['price']
                        })
                        total += quantity * product['price']
                except ValueError:
                    continue

    order_number = get_order_number()
    current_date = datetime.now().strftime("%d-%m-%Y")

    # Build the WhatsApp message carefully
    message_parts = [
        f"New Order (Order #{order_number} - {current_date})",
        f"Name: {name}",
        f"Phone: {phone}",
        f"Address: {address}",
        "\nItems:"
    ]

    # Add items to message
    for item in selected_items:
        message_parts.append(f"• {item['name']} ({item['unit']}) - {item['quantity']} × ₹{item['price']} = ₹{item['subtotal']}")

    # Add total
    message_parts.append(f"\nTotal: ₹{total}")

    # Join all parts with newlines
    full_message = "\n".join(message_parts)

    # Properly encode the URL
    whatsapp_url = f"https://wa.me/+918969161759?text={requests.utils.quote(full_message)}"

    return render_template('index.html', grocery_data=grocery_data, show_whatsapp=True, whatsapp_url=whatsapp_url)

# Admin routes
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin.html', error="Invalid credentials", login_page=True)

    return render_template('admin.html', login_page=True)

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/panel')
@login_required
def admin_panel():
    return render_template('admin.html', grocery_data=grocery_data, login_page=False)

# Category operations
@app.route('/admin/add_category', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name', '').strip()
    if name:
        new_category = {
            "id": generate_id([c["id"] for c in grocery_data["categories"]]),
            "name": name,
            "subcategories": []
        }
        grocery_data["categories"].append(new_category)
    return redirect(url_for('admin_panel'))

@app.route('/admin/update_category/<int:category_id>', methods=['POST'])
@login_required
def update_category(category_id):
    name = request.form.get('name', '').strip()
    category = find_category(category_id)
    if category and name:
        category["name"] = name
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_category/<int:category_id>')
@login_required
def delete_category(category_id):
    grocery_data["categories"] = [c for c in grocery_data["categories"] if c["id"] != category_id]
    return redirect(url_for('admin_panel'))

# Subcategory operations
@app.route('/admin/add_subcategory/<int:category_id>', methods=['POST'])
@login_required
def add_subcategory(category_id):
    name = request.form.get('name', '').strip()
    category = find_category(category_id)
    if category and name:
        new_subcategory = {
            "id": generate_id([s["id"] for s in category["subcategories"]]),
            "name": name,
            "products": []
        }
        category["subcategories"].append(new_subcategory)
    return redirect(url_for('admin_panel'))

@app.route('/admin/update_subcategory/<int:category_id>/<int:subcategory_id>', methods=['POST'])
@login_required
def update_subcategory(category_id, subcategory_id):
    name = request.form.get('name', '').strip()
    subcategory = find_subcategory(category_id, subcategory_id)
    if subcategory and name:
        subcategory["name"] = name
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_subcategory/<int:category_id>/<int:subcategory_id>')
@login_required
def delete_subcategory(category_id, subcategory_id):
    category = find_category(category_id)
    if category:
        category["subcategories"] = [s for s in category["subcategories"] if s["id"] != subcategory_id]
    return redirect(url_for('admin_panel'))

# Product operations
@app.route('/admin/add_product/<int:category_id>/<int:subcategory_id>', methods=['POST'])
@login_required
def add_product(category_id, subcategory_id):
    name = request.form.get('name', '').strip()
    price = request.form.get('price', '0')
    available = request.form.get('available') == 'on'
    unit = request.form.get('unit', '1 pc').strip()

    try:
        price = int(price)
    except ValueError:
        price = 0

    subcategory = find_subcategory(category_id, subcategory_id)
    if subcategory and name and price > 0:
        new_product = {
            "id": generate_id([p["id"] for p in subcategory["products"]]),
            "name": name,
            "price": price,
            "available": available,
            "unit": unit
        }
        subcategory["products"].append(new_product)
    return redirect(url_for('admin_panel'))

@app.route('/admin/update_product/<int:category_id>/<int:subcategory_id>/<int:product_id>', methods=['POST'])
@login_required
def update_product(category_id, subcategory_id, product_id):
    name = request.form.get('name', '').strip()
    price = request.form.get('price', '0')
    available = request.form.get('available') == 'on'
    unit = request.form.get('unit', '1 pc').strip()

    try:
        price = int(price)
    except ValueError:
        price = 0

    product = find_product(category_id, subcategory_id, product_id)
    if product and name and price > 0:
        product["name"] = name
        product["price"] = price
        product["available"] = available
        product["unit"] = unit
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_product/<int:category_id>/<int:subcategory_id>/<int:product_id>')
@login_required
def delete_product(category_id, subcategory_id, product_id):
    subcategory = find_subcategory(category_id, subcategory_id)
    if subcategory:
        subcategory["products"] = [p for p in subcategory["products"] if p["id"] != product_id]
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)