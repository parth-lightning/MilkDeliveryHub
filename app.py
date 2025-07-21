from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join('static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Available milk brands
milk_brands = ["Premium", "Regular", "Toned", "Double-Toned", "Organic"]

# Database setup
def get_db_connection():
    conn = sqlite3.connect('dairy_dash.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Create users table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        phone TEXT UNIQUE,
        password TEXT,
        farm_name TEXT,
        address TEXT,
        milkman_id TEXT,
        role TEXT,
        preferences TEXT DEFAULT '{"brand":"Premium","quantity":1}'
    )
    ''')
    
    # Create milkmen table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS milkmen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        password TEXT,
        milkman_id TEXT UNIQUE
    )
    ''')
    
    # Ensure upi_qr column exists
    try:
        conn.execute('ALTER TABLE milkmen ADD COLUMN upi_qr TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create orders table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_phone TEXT,
        delivery_date TEXT,
        brand TEXT,
        quantity REAL,
        notes TEXT,
        price REAL,
        UNIQUE(customer_phone, delivery_date)
    )
    ''')
    
    # Add price column if not exists
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN price REAL')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create deliveries table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_phone TEXT,
        delivery_date TEXT,
        status TEXT,
        UNIQUE(customer_phone, delivery_date)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Ensure upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def generate_milkman_id():
    while True:
        milkman_id = str(random.randint(100000, 999999))
        conn = get_db_connection()
        existing = conn.execute('SELECT milkman_id FROM milkmen WHERE milkman_id = ?', 
                             (milkman_id,)).fetchone()
        conn.close()
        if existing is None:
            return milkman_id

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        farm_name = request.form.get('farm_name')
        
        # Simple validation
        if not all([username, email, password, farm_name]):
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            conn.close()
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Store user
        conn.execute('INSERT INTO users (username, email, password, farm_name, role) VALUES (?, ?, ?, ?, ?)',
                  (username, email, generate_password_hash(password), farm_name, 'admin'))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/register_milkman', methods=['GET', 'POST'])
def register_milkman():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        # Simple validation
        if not all([name, phone, password]):
            flash('All fields are required', 'error')
            return render_template('register_milkman.html')
        
        conn = get_db_connection()
        existing_milkman = conn.execute('SELECT * FROM milkmen WHERE phone = ?', (phone,)).fetchone()
        
        if existing_milkman:
            conn.close()
            flash('Phone number already registered', 'error')
            return render_template('register_milkman.html')
        
        # Generate unique milkman ID
        milkman_id = generate_milkman_id()
        
        # Store milkman
        conn.execute('INSERT INTO milkmen (name, phone, password, milkman_id) VALUES (?, ?, ?, ?)',
                  (name, phone, generate_password_hash(password), milkman_id))
        conn.commit()
        conn.close()
        
        session['user'] = phone
        session['role'] = 'milkman'
        flash('Registration successful!', 'success')
        return redirect(url_for('milkman_dashboard'))
    
    return render_template('register_milkman.html')

@app.route('/register_customer', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        password = request.form.get('password')
        milkman_id = request.form.get('milkman_id')
        
        # Simple validation
        if not all([name, email, phone, address, password, milkman_id]):
            flash('All fields are required', 'error')
            return render_template('register_customer.html')
        
        conn = get_db_connection()
        existing_customer = conn.execute('SELECT * FROM users WHERE phone = ?', (phone,)).fetchone()
        
        if existing_customer:
            conn.close()
            flash('Phone number already registered', 'error')
            return render_template('register_customer.html')
        
        # Validate milkman ID
        milkman = conn.execute('SELECT * FROM milkmen WHERE milkman_id = ?', (milkman_id,)).fetchone()
        
        if not milkman:
            conn.close()
            flash('Invalid Milkman ID', 'error')
            return render_template('register_customer.html')
        
        # Store customer with default preferences
        default_preferences = json.dumps({"brand": milk_brands[0], "quantity": 1})
        
        conn.execute('''
            INSERT INTO users (username, email, phone, password, address, milkman_id, role, preferences) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, generate_password_hash(password), address, milkman_id, 'customer', default_preferences))
        
        conn.commit()
        conn.close()
        
        session['user'] = phone
        session['role'] = 'customer'
        flash('Registration successful!', 'success')
        return redirect(url_for('customer_dashboard'))
    
    return render_template('register_customer.html', milk_brands=milk_brands)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user'] = email
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/login_milkman', methods=['GET', 'POST'])
def login_milkman():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        conn = get_db_connection()
        milkman = conn.execute('SELECT * FROM milkmen WHERE phone = ?', (phone,)).fetchone()
        conn.close()
        
        if milkman and check_password_hash(milkman['password'], password):
            session['user'] = phone
            session['role'] = 'milkman'
            flash('Login successful!', 'success')
            return redirect(url_for('milkman_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login_milkman.html')

@app.route('/login_customer', methods=['GET', 'POST'])
def login_customer():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        conn = get_db_connection()
        customer = conn.execute('SELECT * FROM users WHERE phone = ? AND role = ?', 
                             (phone, 'customer')).fetchone()
        conn.close()
        
        if customer and check_password_hash(customer['password'], password):
            session['user'] = phone
            session['role'] = 'customer'
            flash('Login successful!', 'success')
            return redirect(url_for('customer_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login_customer.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    role = session.get('role', 'admin')
    
    if role == 'milkman':
        return redirect(url_for('milkman_dashboard'))
    elif role == 'customer':
        return redirect(url_for('customer_dashboard'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (session['user'],)).fetchone()
    conn.close()
    
    return render_template('dashboard.html', user=user)

@app.route('/milkman_dashboard', methods=['GET', 'POST'])
def milkman_dashboard():
    if 'user' not in session or session.get('role') != 'milkman':
        return redirect(url_for('login_milkman'))
    
    conn = get_db_connection()
    milkman = conn.execute('SELECT * FROM milkmen WHERE phone = ?', (session['user'],)).fetchone()

    # Handle QR code upload
    if request.method == 'POST' and 'upi_qr' in request.files:
        file = request.files['upi_qr']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"milkman_{milkman['milkman_id']}_qr.{file.filename.rsplit('.', 1)[1].lower()}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(filepath)
                conn.execute('UPDATE milkmen SET upi_qr = ? WHERE milkman_id = ?', (f'images/{filename}', milkman['milkman_id']))
                conn.commit()
                flash('UPI QR code uploaded successfully!', 'success')
                milkman = conn.execute('SELECT * FROM milkmen WHERE phone = ?', (session['user'],)).fetchone()
            except Exception as e:
                flash(f'Error saving file: {e}', 'error')
        else:
            flash('Invalid file type. Please upload an image file.', 'error')

    # Get selected date from query string, default to tomorrow
    if request.method == 'POST' and 'selected_date' in request.form:
        selected_date = request.form.get('selected_date')
    else:
        selected_date = request.args.get('selected_date')
    if not selected_date:
        selected_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    # Get all orders for selected date from all linked customers
    next_day_orders = []
    deliveries = conn.execute('SELECT * FROM deliveries WHERE delivery_date = ?', (selected_date,)).fetchall()
    delivered_phones = {d['customer_phone'] for d in deliveries if d['status'] == 'delivered'}
    customers = conn.execute('''
        SELECT * FROM users 
        WHERE milkman_id = ? AND role = 'customer'
    ''', (milkman['milkman_id'],)).fetchall()
    for customer in customers:
        preferences = customer['preferences']
        if isinstance(preferences, str):
            preferences = json.loads(preferences)
        order = conn.execute('''
            SELECT * FROM orders 
            WHERE customer_phone = ? AND delivery_date = ?
        ''', (customer['phone'], selected_date)).fetchone()
        if order:
            next_day_orders.append({
                'customer_name': customer['username'],
                'address': customer['address'],
                'brand': order['brand'],
                'quantity': order['quantity'],
                'notes': order['notes'],
                'phone': customer['phone'],
                'delivered': customer['phone'] in delivered_phones
            })
        else:
            next_day_orders.append({
                'customer_name': customer['username'],
                'address': customer['address'],
                'brand': preferences['brand'],
                'quantity': preferences['quantity'],
                'notes': '',
                'phone': customer['phone'],
                'delivered': customer['phone'] in delivered_phones
            })
    customer_list = []
    for customer in customers:
        customer_list.append({
            'name': customer['username'],
            'phone': customer['phone'],
            'address': customer['address'],
            'email': customer['email'] if customer['email'] else ''
        })
    conn.close()
    return render_template('milkman_dashboard.html', milkman=milkman, orders=next_day_orders, customers=customer_list, next_day=selected_date, selected_date=selected_date)

@app.route('/customer_dashboard')
def customer_dashboard():
    if 'user' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))
    
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM users WHERE phone = ?', (session['user'],)).fetchone()
    
    # Find milkman name
    milkman = conn.execute('SELECT * FROM milkmen WHERE milkman_id = ?', 
                        (customer['milkman_id'],)).fetchone()
    
    milkman_name = milkman['name'] if milkman else "Unknown"
    conn.close()
    
    return render_template('customer_dashboard.html', customer=customer, milkman_name=milkman_name)

@app.route('/milk_preference', methods=['GET', 'POST'])
def milk_preference():
    if 'user' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))
    
    customer_phone = session['user']
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM users WHERE phone = ?', (customer_phone,)).fetchone()
    
    preferences = json.loads(customer['preferences'])
    
    if request.method == 'POST':
        brand = request.form.get('brand')
        quantity = float(request.form.get('quantity'))
        date = request.form.get('date')
        notes = request.form.get('notes', '')
        price = float(request.form.get('price', 50))  # Default to 50 if not set
        
        # Update default preferences if selected
        if request.form.get('update_default') == 'on':
            new_preferences = json.dumps({"brand": brand, "quantity": quantity})
            conn.execute('UPDATE users SET preferences = ? WHERE phone = ?', 
                      (new_preferences, customer_phone))
        
        # Save specific order for the date
        try:
            conn.execute('''
                INSERT INTO orders (customer_phone, delivery_date, brand, quantity, notes, price)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (customer_phone, date, brand, quantity, notes, price))
        except sqlite3.IntegrityError:
            conn.execute('''
                UPDATE orders 
                SET brand = ?, quantity = ?, notes = ?, price = ?
                WHERE customer_phone = ? AND delivery_date = ?
            ''', (brand, quantity, notes, price, customer_phone, date))
        
        conn.commit()
        flash('Milk preference updated successfully!', 'success')
        return redirect(url_for('milk_preference'))
    
    # Get all orders for this customer
    customer_orders = {}
    orders = conn.execute('SELECT * FROM orders WHERE customer_phone = ? ORDER BY delivery_date', 
                       (customer_phone,)).fetchall()
    
    for order in orders:
        customer_orders[order['delivery_date']] = {
            'brand': order['brand'],
            'quantity': order['quantity'],
            'notes': order['notes']
        }
    
    conn.close()
    
    # Update the customer object with parsed preferences for template
    customer = dict(customer)
    customer['preferences'] = preferences
    
    return render_template('milk_preference.html', 
                          customer=customer, 
                          milk_brands=milk_brands, 
                          orders=customer_orders)

@app.route('/calendar_view')
def calendar_view():
    if 'user' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))
    
    customer_phone = session['user']
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM users WHERE phone = ?', (customer_phone,)).fetchone()
    
    preferences = json.loads(customer['preferences'])
    customer = dict(customer)
    customer['preferences'] = preferences
    
    # Get month and year from query parameters, default to current month/year
    today = datetime.now()
    month = request.args.get('month', default=today.month, type=int)
    year = request.args.get('year', default=today.year, type=int)
    
    # Get the first day of the month and the number of days in the month
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    num_days = last_day.day
    first_weekday = first_day.weekday()  # Monday=0, Sunday=6
    # Adjust to Sunday=0, Saturday=6
    first_weekday = (first_weekday + 1) % 7
    
    # Get all delivery data for this customer for the selected month
    deliveries_data = conn.execute('''
        SELECT * FROM deliveries 
        WHERE customer_phone = ? AND delivery_date LIKE ?
    ''', (customer_phone, f"{year}-{month:02d}-%")).fetchall()
    
    orders_data = conn.execute('''
        SELECT * FROM orders 
        WHERE customer_phone = ? AND delivery_date LIKE ?
    ''', (customer_phone, f"{year}-{month:02d}-%")).fetchall()
    
    # Create dictionaries for easier lookup
    customer_deliveries = {row['delivery_date']: row for row in deliveries_data}
    customer_orders = {row['delivery_date']: {
        'brand': row['brand'],
        'quantity': row['quantity'],
        'notes': row['notes']
    } for row in orders_data}
    
    conn.close()
    
    # Create calendar data
    calendar_data = []
    # Pad empty days before the 1st
    for _ in range(first_weekday):
        calendar_data.append({'day': '', 'status': 'empty', 'order': None})
    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        status = "not_ordered"
        if date_str in customer_deliveries:
            status = "delivered"
        elif date_str in customer_orders:
            if datetime.now() > datetime.strptime(date_str, '%Y-%m-%d'):
                status = "delivered"  # For demo purposes, assume delivered if in the past
            else:
                status = "ordered"
        calendar_data.append({
            'day': day,
            'status': status,
            'order': customer_orders.get(date_str)
        })
    # Pad empty days at the end to complete the last week
    while len(calendar_data) % 7 != 0:
        calendar_data.append({'day': '', 'status': 'empty', 'order': None})
    
    # Calculate previous and next month/year
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    
    return render_template('calendar_view.html', 
                          customer=customer, 
                          calendar_data=calendar_data,
                          month=month,
                          year=year,
                          month_name=first_day.strftime('%B'),
                          prev_month=prev_month,
                          prev_year=prev_year,
                          next_month=next_month,
                          next_year=next_year)

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'user' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))
    
    customer_phone = session['user']
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM users WHERE phone = ?', (customer_phone,)).fetchone()
    
    if request.method == 'POST':
        address = request.form.get('address')
        milkman_id = request.form.get('milkman_id')
        
        # Validate milkman ID
        milkman = conn.execute('SELECT * FROM milkmen WHERE milkman_id = ?', (milkman_id,)).fetchone()
        
        if not milkman:
            conn.close()
            flash('Invalid Milkman ID', 'error')
            return redirect(url_for('update_profile'))
        
        # Update customer profile
        conn.execute('UPDATE users SET address = ?, milkman_id = ? WHERE phone = ?', 
                  (address, milkman_id, customer_phone))
        conn.commit()
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('customer_dashboard'))
    
    conn.close()
    
    return render_template('update_profile.html', customer=customer)

@app.route('/cancel_order/<date>')
def cancel_order(date):
    if 'user' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))
    
    customer_phone = session['user']
    
    # Check if the order is for a future date
    order_date = datetime.strptime(date, '%Y-%m-%d')
    cutoff_date = datetime.now().replace(hour=23, minute=59, second=59)
    if order_date < cutoff_date:
        flash('Cannot cancel orders for today or past dates', 'error')
        return redirect(url_for('milk_preference'))
    
    # Remove the order
    conn = get_db_connection()
    result = conn.execute('DELETE FROM orders WHERE customer_phone = ? AND delivery_date = ?', 
                      (customer_phone, date))
    conn.commit()
    conn.close()
    
    if result.rowcount > 0:
        flash('Order cancelled successfully!', 'success')
    else:
        flash('Order not found', 'error')
    
    return redirect(url_for('milk_preference'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('home'))

@app.route('/payment')
def payment():
    if 'user' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))

    customer_phone = session['user']
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM users WHERE phone = ?', (customer_phone,)).fetchone()
    milkman = conn.execute('SELECT * FROM milkmen WHERE milkman_id = ?', (customer['milkman_id'],)).fetchone()

    # Assume upi_qr is a field in milkmen table, or use a placeholder if not present
    upi_qr = milkman['upi_qr'] if milkman and 'upi_qr' in milkman.keys() else url_for('static', filename='images/placeholder.svg')

    # Calculate remaining amount to pay (sum of delivered orders minus payments)
    # For simplicity, assume 1L = 50 currency units, and no payment tracking table
    orders = conn.execute('SELECT * FROM orders WHERE customer_phone = ?', (customer_phone,)).fetchall()
    deliveries = conn.execute('SELECT * FROM deliveries WHERE customer_phone = ? AND status = "delivered"', (customer_phone,)).fetchall()
    total_due = 0
    for delivery in deliveries:
        date = delivery['delivery_date']
        order = next((o for o in orders if o['delivery_date'] == date), None)
        if order:
            price = order['price'] if order['price'] is not None else 50
            total_due += order['quantity'] * price
        else:
            preferences = json.loads(customer['preferences']) if isinstance(customer['preferences'], str) else customer['preferences']
            total_due += preferences['quantity'] * 50
    amount_remaining = total_due
    conn.close()
    return render_template('payment.html', upi_qr=upi_qr, amount_remaining=amount_remaining, milkman=milkman)

@app.route('/mark_delivered', methods=['POST'])
def mark_delivered():
    if 'user' not in session or session.get('role') != 'milkman':
        return redirect(url_for('login_milkman'))
    customer_phone = request.form.get('customer_phone')
    delivery_date = request.form.get('delivery_date')
    if not customer_phone or not delivery_date:
        flash('Invalid request.', 'error')
        return redirect(url_for('milkman_dashboard'))
    conn = get_db_connection()
    # Insert or update delivery status
    try:
        conn.execute('''
            INSERT INTO deliveries (customer_phone, delivery_date, status)
            VALUES (?, ?, ?)
            ON CONFLICT(customer_phone, delivery_date) DO UPDATE SET status=excluded.status
        ''', (customer_phone, delivery_date, 'delivered'))
        conn.commit()
        flash('Marked as delivered.', 'success')
    except Exception as e:
        flash(f'Error marking as delivered: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('milkman_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
