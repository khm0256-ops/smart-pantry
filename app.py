from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
import sqlite3
from datetime import datetime
import os
import sys
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY', 'dev-secret-change-me')  # مهم للـ flash messages

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(id=user['id'], username=user['username'])
    return None

def get_resource_path(relative_path):
    """الحصول على المسار الصحيح للملفات"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_db_connection():
    """الاتصال بقاعدة البيانات"""
    # حفظ قاعدة البيانات في مجلد المستخدم لضمان الكتابة
    db_path = os.path.join(os.path.expanduser('~'), 'smart_pantry.db')
    print(f"📁 مسار قاعدة البيانات: {db_path}")  # طباعة المسار للتأكد
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """إنشاء الجداول إذا لم تكن موجودة"""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT NOT NULL,
            name_en TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            min_quantity INTEGER DEFAULT 2,
            expiry_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # users table for authentication
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    # طباعة عدد الأصناف الحالية
    items_count = conn.execute('SELECT COUNT(*) FROM items').fetchone()[0]
    users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    print(f"📊 عدد الأصناف: {items_count}, عدد المستخدمين: {users_count}")
    conn.close()

# تهيئة قاعدة البيانات عند بدء التطبيق
init_db()

@app.route('/')
@login_required
def index():
    """الصفحة الرئيسية"""
    init_db()
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items ORDER BY id DESC').fetchall()
    conn.close()
    inventory = []
    shopping_list = []
    today = datetime.now().date()
    for item in items:
        days_left = 999
        status = "good"
        if item['expiry_date']:
            try:
                exp_date_obj = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                days_left = (exp_date_obj - today).days
                if days_left < 0:
                    status = "expired"
                elif days_left <= 7:
                    status = "warning"
            except:
                pass
        need_buy = item['quantity'] <= item['min_quantity']
        item_obj = {
            'id': item['id'],
            'name_ar': item['name_ar'],
            'name_en': item['name_en'],
            'qty': item['quantity'],
            'min': item['min_quantity'],
            'expiry': item['expiry_date'],
            'days_left': days_left,
            'status': status,
            'need_buy': need_buy
        }
        inventory.append(item_obj)
        if need_buy:
            shopping_list.append(item_obj)
    return render_template('index.html', inventory=inventory, shopping_list=shopping_list)

def _ensure_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']

@app.before_request
def csrf_protect():
    if request.method == 'POST':
        token = session.get('csrf_token')
        form_token = request.form.get('csrf_token')
        if not token or token != form_token:
            abort(400)

@app.context_processor
def inject_csrf():
    return {'csrf_token': _ensure_csrf_token()}

@app.route('/page2')
@login_required
def page2():
    return render_template('page2.html')

@app.route('/add', methods=['POST'])
@login_required
def add_item():
    """إضافة صنف جديد"""
    try:
        name_ar = request.form.get('name_ar', '').strip()
        name_en = request.form.get('name_en', '').strip()
        quantity = int(request.form.get('quantity', 1))
        min_qty = int(request.form.get('min_quantity', 2))
        expiry = request.form.get('expiry_date', '').strip()
        
        # التحقق من البيانات
        if not name_ar or not name_en:
            flash('يرجى إدخال الاسم بالعربي والإنجليزي', 'danger')
            return redirect(url_for('index'))
        
        if quantity < 0 or min_qty < 0:
            flash('الكمية يجب أن تكون رقم موجب', 'danger')
            return redirect(url_for('index'))

        conn = get_db_connection()
        conn.execute('''INSERT INTO items 
                       (name_ar, name_en, quantity, min_quantity, expiry_date) 
                       VALUES (?, ?, ?, ?, ?)''',
                     (name_ar, name_en, quantity, min_qty, expiry if expiry else None))
        conn.commit()
        conn.close()
        
        flash(f'✅ تم إضافة {name_ar} بنجاح', 'success')
        
    except Exception as e:
        flash(f'❌ خطأ في الإضافة: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/update/<int:id>/<action>', methods=['POST'])
@login_required
def update_qty(id, action):
    """تحديث الكمية (زيادة أو نقصان)"""
    try:
        conn = get_db_connection()
        
        if action == 'inc':
            conn.execute('UPDATE items SET quantity = quantity + 1 WHERE id = ?', (id,))
            flash('✅ تم زيادة الكمية', 'success')
        elif action == 'dec':
            conn.execute('UPDATE items SET quantity = MAX(0, quantity - 1) WHERE id = ?', (id,))
            flash('✅ تم تقليل الكمية', 'success')
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        flash(f'❌ خطأ في التحديث: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    """حذف صنف"""
    try:
        conn = get_db_connection()
        item = conn.execute('SELECT name_ar FROM items WHERE id = ?', (id,)).fetchone()
        
        if item:
            conn.execute('DELETE FROM items WHERE id = ?', (id,))
            conn.commit()
            flash(f'✅ تم حذف {item["name_ar"]}', 'success')
        else:
            flash('❌ الصنف غير موجود', 'danger')
        
        conn.close()
        
    except Exception as e:
        flash(f'❌ خطأ في الحذف: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/clear_all', methods=['POST'])
@login_required
def clear_all():
    """حذف جميع الأصناف (للتجربة)"""
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM items')
        conn.commit()
        conn.close()
        flash('✅ تم حذف جميع الأصناف', 'success')
    except Exception as e:
        flash(f'❌ خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """تسجيل مستخدم جديد"""
    init_db()  # تأكد من إنشاء الجداول
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('يرجى ملء جميع الحقول', 'danger')
            return redirect(url_for('register'))

        try:
            conn = get_db_connection()
            existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            if existing:
                flash('اسم المستخدم مستخدم مسبقًا', 'danger')
                conn.close()
                return redirect(url_for('register'))

            pwd_hash = generate_password_hash(password)
            conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, pwd_hash))
            conn.commit()
            conn.close()
            flash('تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'خطأ في التسجيل: {str(e)}', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """تسجيل الدخول"""
    init_db()  # تأكد من إنشاء الجداول
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('يرجى ملء جميع الحقول', 'danger')
            return redirect(url_for('login'))

        try:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                user_obj = User(id=user['id'], username=user['username'])
                login_user(user_obj)
                flash('تم تسجيل الدخول بنجاح', 'success')
                return redirect(url_for('index'))
            else:
                flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
        except Exception as e:
            flash(f'خطأ في تسجيل الدخول: {str(e)}', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج', 'info')
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    """معالجة خطأ 404"""
    return render_template('error.html', error="الصفحة غير موجودة"), 404

@app.errorhandler(500)
def internal_error(e):
    """معالجة خطأ 500"""
    return render_template('error.html', error="خطأ في السيرفر"), 500

@app.route('/health')
def health():
    return jsonify({"ok": True}), 200

@app.route('/barcode/lookup')
@login_required
def barcode_lookup():
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({"ok": False, "error": "missing code"}), 400
    name_en = None
    name_ar = None
    try:
        import requests
        resp = requests.get(f'https://world.openfoodfacts.org/api/v0/product/{code}.json', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 1:
                prod = data.get('product', {})
                name_en = prod.get('product_name_en') or prod.get('product_name')
                name_ar = prod.get('product_name_ar') or name_en
    except Exception:
        pass
    if not name_en:
        name_en = f'Item {code}'
    if not name_ar:
        name_ar = name_en
    return jsonify({"ok": True, "code": code, "name_en": name_en, "name_ar": name_ar})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("⚠️  استخدم ملف run.py لتشغيل التطبيق")
    app.run(host='0.0.0.0', debug=False, port=port)