from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date, timedelta
import sqlite3
import hashlib
import uuid
import random
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "mysecretkey123456789"
app.permanent_session_lifetime = timedelta(days=365)

# ====== تنظیمات آپلود عکس و موسیقی ======
UPLOAD_FOLDER = 'static/profile_pics'
MUSIC_FOLDER = 'static/music'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_MUSIC_EXTENSIONS = {'mp3', 'wav', 'ogg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MUSIC_FOLDER'] = MUSIC_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_music_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MUSIC_EXTENSIONS

# ====== بارگذاری فایل‌های ترجمه ======
def load_translations(lang):
    try:
        with open(f'locales/{lang}.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        with open('locales/fa.json', 'r', encoding='utf-8') as f:
            return json.load(f)

def get_db():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            profile_image TEXT DEFAULT 'default.png',
            language TEXT DEFAULT 'fa',
            meditation_music TEXT DEFAULT '',
            subscription_type TEXT DEFAULT 'trial',
            subscription_end DATE,
            invite_code TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            date DATE NOT NULL,
            priority INTEGER DEFAULT 3,
            done BOOLEAN DEFAULT FALSE,
            category TEXT DEFAULT 'شخصی',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT CHECK (type IN ('income', 'expense')),
            category TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🔥',
            color TEXT DEFAULT '#4A90D9',
            frequency TEXT DEFAULT 'daily',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            date DATE NOT NULL,
            done BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            invited_email TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inviter_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            mood TEXT,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS language_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            language TEXT NOT NULL,
            level TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            vocabulary TEXT,
            quiz TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_invite_code():
    return str(uuid.uuid4())[:8]

def get_subscription_status(user_id):
    conn = get_db()
    user = conn.execute('SELECT subscription_type, subscription_end FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if not user:
        return None
    if user['subscription_end']:
        end_date = date.fromisoformat(user['subscription_end'])
        if end_date >= date.today():
            return user['subscription_type']
    return 'free'

def is_premium(user_id):
    status = get_subscription_status(user_id)
    return status in ['trial', 'weekly', 'monthly', 'yearly']

def get_motivational_message():
    messages = [
        "هر روز یک قدم به نسخه‌ی بهتر خودت نزدیک‌تر شو.",
        "بزرگ‌ترین سفر با یک قدم شروع می‌شود.",
        "امروز روز تغییر توست.",
        "به خودت ایمان داشته باش، توانش را داری.",
        "همین الان شروع کن، عالی خواهد شد.",
        "هر روزت را با عشق شروع کن.",
        "تو می‌تونی! فقط باور کن."
    ]
    return random.choice(messages)

def get_user_language(user_id):
    conn = get_db()
    user = conn.execute('SELECT language FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user['language'] if user else 'fa'

# ====== اضافه کردن درس‌های نمونه ======
def add_sample_lessons():
    conn = get_db()
    cursor = conn.cursor()
    
    count = cursor.execute('SELECT COUNT(*) FROM language_lessons').fetchone()[0]
    if count > 0:
        conn.close()
        return
    
    lessons = [
        ('english', 'beginner', 'سلام و احوالپرسی', 
         'در این درس با سلام و احوالپرسی به انگلیسی آشنا می‌شوید.\n\nHello = سلام\nGood morning = صبح بخیر\nHow are you? = حال شما چطور است؟\nI\'m fine = خوبم',
         'Hello, Good morning, How are you?, I\'m fine',
         'سلام به انگلیسی چه میشود؟\nالف) Hello\nب) Goodbye'),
        ('english', 'beginner', 'اعداد و شمارش', 
         'در این درس اعداد ۱ تا ۱۰ را یاد می‌گیرید.\n\nOne = ۱\nTwo = ۲\nThree = ۳\nFour = ۴\nFive = ۵',
         'One, Two, Three, Four, Five',
         'عدد ۳ به انگلیسی چیست؟\nالف) Two\nب) Three'),
        ('arabic', 'beginner', 'التحية (سلام و احوالپرسی)', 
         'في هذا الدرس تتعلم التحية بالعربية.\n\nالسلام علیکم = سلام\nصباح الخیر = صبح بخیر\nکیف حالک؟ = حال شما چطور است؟\nبخیر = خوبم',
         'السلام علیکم, صباح الخیر, کیف حالک؟, بخیر',
         'سلام به عربی چه میشود؟\nالف) السلام علیکم\nب) صباح الخیر'),
        ('arabic', 'beginner', 'الأرقام (اعداد)', 
         'في هذا الدرس تتعلم الأرقام من ۱ إلى ۱۰.\n\nواحد = ۱\nإثنان = ۲\nثلاثة = ۳\nأربعة = ۴\nخمسة = ۵',
         'واحد, إثنان, ثلاثة, أربعة, خمسة',
         'عدد ۳ به عربی چیست؟\nالف) إثنان\nب) ثلاثة'),
    ]
    
    for lesson in lessons:
        cursor.execute('''
            INSERT INTO language_lessons (language, level, title, content, vocabulary, quiz)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', lesson)
    
    conn.commit()
    conn.close()

add_sample_lessons()

# ======================== صفحات اصلی ========================

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    today = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    user = cursor.execute('SELECT username, full_name, profile_image, language FROM users WHERE id = ?', (user_id,)).fetchone()
    username = user['username'] if user else 'کاربر'
    profile_image = user['profile_image'] if user else 'default.png'
    user_lang = user['language'] if user else 'fa'
    translations = load_translations(user_lang)
    
    tasks = cursor.execute('SELECT * FROM tasks WHERE user_id = ? AND date = ?', (user_id, today)).fetchall()
    tasks_count = len(tasks)
    done_count = sum(1 for t in tasks if t['done'])
    completion = int((done_count / tasks_count * 100)) if tasks_count > 0 else 0
    
    expense = cursor.execute('SELECT SUM(amount) as total FROM transactions WHERE user_id = ? AND date = ? AND type = "expense"', (user_id, today)).fetchone()
    today_expense = expense['total'] or 0
    
    habits = cursor.execute('SELECT * FROM habits WHERE user_id = ?', (user_id,)).fetchall()
    habit_progress = []
    for h in habits:
        log = cursor.execute('SELECT * FROM habit_logs WHERE habit_id = ? AND date = ?', (h['id'], today)).fetchone()
        habit_progress.append({
            'id': h['id'],
            'name': h['name'],
            'emoji': h['emoji'],
            'color': h['color'],
            'done': log is not None
        })
    
    sub_info = cursor.execute('SELECT subscription_type, subscription_end FROM users WHERE id = ?', (user_id,)).fetchone()
    is_premium_user = is_premium(user_id)
    conn.close()
    
    return render_template('index.html',
                         username=username,
                         profile_image=profile_image,
                         welcome_message=translations.get('welcome', 'سلام {name} عزیز! 🌸').format(name=username),
                         motivational_message=get_motivational_message(),
                         tasks=tasks,
                         tasks_count=tasks_count,
                         done_count=done_count,
                         completion=completion,
                         today_expense=today_expense,
                         habits=habit_progress,
                         today=today,
                         total_habits=len(habits),
                         done_habits=sum(1 for h in habit_progress if h['done']),
                         is_premium=is_premium_user,
                         subscription_type=sub_info['subscription_type'] if sub_info else 'free',
                         translations=translations,
                         current_lang=user_lang)

# ======================== تنظیمات زبان ========================

@app.route('/set_language/<lang>')
def set_language(lang):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if lang not in ['fa', 'en', 'ar']:
        return "زبان نامعتبر"
    conn = get_db()
    conn.execute('UPDATE users SET language = ? WHERE id = ?', (lang, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('index'))

# ======================== احراز هویت ========================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = hash_password(request.form['password'])
        full_name = request.form.get('full_name', '')
        conn = get_db()
        try:
            invite_code = generate_invite_code()
            trial_end = date.today() + timedelta(days=5)
            conn.execute('''
                INSERT INTO users (username, email, password, full_name, subscription_type, subscription_end, invite_code)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, email, password, full_name, 'trial', trial_end.isoformat(), invite_code))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return "این نام کاربری یا ایمیل قبلاً ثبت شده است"
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        remember = request.form.get('remember')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['username'] = user['username']
            session.permanent = True if remember else False
            return redirect(url_for('index'))
        else:
            return "ایمیل یا رمز عبور اشتباه است"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ======================== پروفایل ========================

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{session['user_id']}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                conn.execute('UPDATE users SET profile_image = ? WHERE id = ?', (filename, session['user_id']))
        if full_name:
            conn.execute('UPDATE users SET full_name = ? WHERE id = ?', (full_name, session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('profile'))
    conn.close()
    return render_template('profile.html', user=user)

# ======================== اشتراک ========================

@app.route('/subscription')
def subscription():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    user = conn.execute('SELECT subscription_type, subscription_end FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('subscription.html', current=user['subscription_type'], end=user['subscription_end'])

@app.route('/buy_subscription/<plan>')
def buy_subscription(plan):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    plans = {'weekly': 7, 'monthly': 30, 'yearly': 365}
    if plan not in plans:
        return "طرح نامعتبر"
    days = plans[plan]
    new_end = date.today() + timedelta(days=days)
    conn = get_db()
    conn.execute('UPDATE users SET subscription_type = ?, subscription_end = ? WHERE id = ?', (plan, new_end.isoformat(), session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('subscription'))

# ======================== دعوت از دوستان ========================

@app.route('/invite')
def invite():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    user = conn.execute('SELECT invite_code FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    invites = conn.execute('SELECT * FROM invites WHERE inviter_id = ?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('invite.html', invite_code=user['invite_code'], invites=invites)

# ======================== مطالعه ========================

@app.route('/study_techniques')
def study_techniques():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_premium(session['user_id']):
        return redirect(url_for('subscription'))
    techniques = [
        {'id': 1, 'name': 'پومودورو', 'desc': '۲۵ دقیقه کار، ۵ دقیقه استراحت'},
        {'id': 2, 'name': 'تکنیک فاینمن', 'desc': 'یادگیری با آموزش به دیگران'},
        {'id': 3, 'name': '۵۰/۱۰', 'desc': '۵۰ دقیقه مطالعه، ۱۰ دقیقه استراحت'},
        {'id': 4, 'name': 'تکنیک ۲/۵/۷', 'desc': 'مرور در روزهای ۲، ۵ و ۷'},
        {'id': 5, 'name': 'نقشه ذهنی', 'desc': 'ایجاد نقشه برای درک بهتر مطالب'},
        {'id': 6, 'name': 'خواندن فعال', 'desc': 'یادداشت‌برداری و سوال پرسیدن هنگام مطالعه'},
        {'id': 7, 'name': 'تکنیک ۱۰۰۰ ساعت', 'desc': '۱۰۰۰ ساعت تمرکز روی یک مهارت'},
    ]
    return render_template('study_techniques.html', techniques=techniques)

@app.route('/technique/<int:tech_id>')
def technique_detail(tech_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_premium(session['user_id']):
        return redirect(url_for('subscription'))
    techniques = [
        {'id': 1, 'name': 'پومودورو', 'desc': '۲۵ دقیقه کار، ۵ دقیقه استراحت', 
         'full': 'تکنیک پومودورو یک روش مدیریت زمان است که توسط فرانچسکو سیریلو در دهه ۱۹۸۰ ابداع شد. در این روش، شما ۲۵ دقیقه به صورت متمرکز روی یک کار کار می‌کنید و سپس ۵ دقیقه استراحت می‌کنید. بعد از ۴ دوره، یک استراحت طولانی‌تر (۱۵-۳۰ دقیقه) انجام می‌دهید.',
         'steps': ['یک کار را انتخاب کنید', 'تایمر را روی ۲۵ دقیقه تنظیم کنید', 'روی کار تمرکز کنید', '۵ دقیقه استراحت کنید', 'بعد از ۴ دوره، ۱۵-۳۰ دقیقه استراحت کنید'],
         'tip': 'اگر در حین کار حواس‌تان پرت شد، آن را یادداشت کنید و بعداً پیگیری کنید.'},
        {'id': 2, 'name': 'تکنیک فاینمن', 'desc': 'یادگیری با آموزش به دیگران', 
         'full': 'ریچارد فاینمن، فیزیکدان برنده جایزه نوبل، معتقد بود بهترین راه برای یادگیری یک مطلب، آموزش آن به دیگران است. در این روش، شما مطلب را به زبانی ساده و روان توضیح می‌دهید تا مطمئن شوید خودتان کاملاً آن را درک کرده‌اید.',
         'steps': ['مطلب را انتخاب کنید', 'آن را به یک کودک ۱۰ ساله توضیح دهید', 'جاهایی که گیر کردید را شناسایی کنید', 'دوباره مطالعه کنید و ساده‌تر توضیح دهید'],
         'tip': 'اگر نمی‌توانید ساده توضیح دهید، یعنی خودتان کامل متوجه نشده‌اید.'},
        {'id': 3, 'name': '۵۰/۱۰', 'desc': '۵۰ دقیقه مطالعه، ۱۰ دقیقه استراحت', 
         'full': 'این روش مشابه پومودورو است اما با زمان‌های طولانی‌تر. ۵۰ دقیقه مطالعه متمرکز و ۱۰ دقیقه استراحت. مناسب برای افرادی که می‌توانند تمرکز طولانی‌تری داشته باشند.',
         'steps': ['۵۰ دقیقه مطالعه متمرکز', '۱۰ دقیقه استراحت کامل', 'تکرار تا ۴ دوره'],
         'tip': 'در زمان استراحت، از گوشی استفاده نکنید. بایستید و قدم بزنید.'},
        {'id': 4, 'name': 'تکنیک ۲/۵/۷', 'desc': 'مرور در روزهای ۲، ۵ و ۷', 
         'full': 'این تکنیک بر اساس منحنی فراموشی ابینگهاوس طراحی شده است. شما یک مطلب را در روزهای ۲، ۵ و ۷ بعد از یادگیری مرور می‌کنید تا در حافظه بلندمدت تثبیت شود.',
         'steps': ['روز اول: یادگیری مطلب', 'روز دوم: مرور سریع', 'روز پنجم: مرور عمیق', 'روز هفتم: مرور نهایی'],
         'tip': 'بهترین زمان مرور، صبح زود یا قبل از خواب است.'},
        {'id': 5, 'name': 'نقشه ذهنی', 'desc': 'ایجاد نقشه برای درک بهتر مطالب', 
         'full': 'نقشه ذهنی یک روش گرافیکی برای سازماندهی اطلاعات است. شما یک موضوع اصلی را در مرکز قرار می‌دهید و شاخه‌های فرعی را به آن متصل می‌کنید. این روش به درک بهتر روابط بین مفاهیم کمک می‌کند.',
         'steps': ['موضوع اصلی را در مرکز بنویسید', 'شاخه‌های اصلی را اضافه کنید', 'برای هر شاخه، زیرشاخه‌ها را بنویسید', 'از رنگ‌ها و تصاویر استفاده کنید'],
         'tip': 'از کاغذ بزرگ استفاده کنید و خلاقیت به خرج دهید.'},
        {'id': 6, 'name': 'خواندن فعال', 'desc': 'یادداشت‌برداری و سوال پرسیدن هنگام مطالعه', 
         'full': 'در این روش، شما به جای خواندن منفعل، با متن درگیر می‌شوید. سوال می‌پرسید، یادداشت برمی‌دارید، خلاصه‌نویسی می‌کنید و نکات کلیدی را مشخص می‌کنید. این روش باعث درک عمیق‌تر مطالب می‌شود.',
         'steps': ['قبل از خواندن، سوالاتی بنویسید', 'هنگام خواندن، نکات کلیدی را یادداشت کنید', 'بعد از خواندن، خلاصه‌ای بنویسید', 'مطالب را به دیگران آموزش دهید'],
         'tip': 'با مداد یا ماژیک هایلایت کار کنید تا تعامل بیشتری داشته باشید.'},
        {'id': 7, 'name': 'تکنیک ۱۰۰۰ ساعت', 'desc': '۱۰۰۰ ساعت تمرکز روی یک مهارت', 
         'full': 'این تکنیک بر اساس قانون ۱۰۰۰۰ ساعت مالکوم گلدول طراحی شده است. اما نسخه ساده‌تر آن، ۱۰۰۰ ساعت تمرکز روی یک مهارت خاص است. با ۱۰۰۰ ساعت تمرین هدفمند، می‌توانید در هر مهارتی به سطح بالایی از تسلط برسید.',
         'steps': ['یک مهارت را انتخاب کنید', 'هر روز حداقل ۲ ساعت تمرین کنید', 'پیشرفت خود را ثبت کنید', 'هر هفته مرور و بهبود'],
         'tip': 'کیفیت مهم‌تر از کمیت است. تمرین هدفمند انجام دهید.'}
    ]
    tech = next((t for t in techniques if t['id'] == tech_id), None)
    if not tech:
        return "تکنیک پیدا نشد"
    return render_template('technique_detail.html', technique=tech)

# ======================== چت‌بات ========================

@app.route('/chatbot')
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_premium(session['user_id']):
        return redirect(url_for('subscription'))
    return render_template('chatbot.html')

# ======================== ژورنال ========================

@app.route('/journal', methods=['GET', 'POST'])
def journal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_premium(session['user_id']):
        return redirect(url_for('subscription'))
    
    user_id = session['user_id']
    today = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        mood = request.form.get('mood', '')
        cursor.execute('''
            INSERT INTO journal_entries (user_id, title, content, mood, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, title, content, mood, today))
        conn.commit()
        conn.close()
        return redirect(url_for('journal'))
    
    entries = cursor.execute('''
        SELECT * FROM journal_entries WHERE user_id = ? ORDER BY date DESC, created_at DESC
    ''', (user_id,)).fetchall()
    conn.close()
    
    return render_template('journal.html', entries=entries, today=today)

# ======================== آموزش زبان ========================

@app.route('/language/<lang>')
def language_home(lang):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_premium(session['user_id']):
        return redirect(url_for('subscription'))
    if lang not in ['english', 'arabic']:
        return "زبان نامعتبر"
    
    conn = get_db()
    lessons = conn.execute('SELECT * FROM language_lessons WHERE language = ? ORDER BY level, id', (lang,)).fetchall()
    conn.close()
    
    return render_template('language_home.html', lang=lang, lessons=lessons)

@app.route('/lesson/<int:lesson_id>')
def lesson_detail(lesson_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_premium(session['user_id']):
        return redirect(url_for('subscription'))
    
    conn = get_db()
    lesson = conn.execute('SELECT * FROM language_lessons WHERE id = ?', (lesson_id,)).fetchone()
    conn.close()
    
    if not lesson:
        return "درس پیدا نشد"
    
    return render_template('lesson_detail.html', lesson=lesson)

# ======================== مدیتیشن ========================

@app.route('/meditation')
def meditation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_premium(session['user_id']):
        return redirect(url_for('subscription'))
    
    conn = get_db()
    user = conn.execute('SELECT meditation_music FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    music_file = user['meditation_music'] if user and user['meditation_music'] else ''
    
    return render_template('meditation.html', music_file=music_file)

@app.route('/upload_music', methods=['POST'])
def upload_music():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not is_premium(session['user_id']):
        return redirect(url_for('subscription'))
    
    if 'music_file' not in request.files:
        return "هیچ فایلی انتخاب نشده است"
    
    file = request.files['music_file']
    if file.filename == '':
        return "هیچ فایلی انتخاب نشده است"
    
    if file and allowed_music_file(file.filename):
        filename = secure_filename(f"{session['user_id']}_{file.filename}")
        file.save(os.path.join(app.config['MUSIC_FOLDER'], filename))
        
        conn = get_db()
        conn.execute('UPDATE users SET meditation_music = ? WHERE id = ?', (filename, session['user_id']))
        conn.commit()
        conn.close()
        
        return redirect(url_for('meditation'))
    
    return "فرمت فایل پشتیبانی نمی‌شود. فقط MP3, WAV, OGG"

# ======================== سایر صفحات ========================

@app.route('/shopping_list')
def shopping_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('shopping_list.html')

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    user = conn.execute('SELECT language FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    current_lang = user['language'] if user else 'fa'
    
    return render_template('settings.html', current_lang=current_lang)

# ======================== وظایف ========================

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('INSERT INTO tasks (user_id, title, date, priority, category) VALUES (?, ?, ?, ?, ?)',
                 (session['user_id'], request.form['title'], request.form['date'], 
                  int(request.form.get('priority', 3)), request.form.get('category', 'شخصی')))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/toggle_task/<int:task_id>')
def toggle_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    task = conn.execute('SELECT done FROM tasks WHERE id = ? AND user_id = ?', (task_id, session['user_id'])).fetchone()
    if task:
        conn.execute('UPDATE tasks SET done = ? WHERE id = ?', (not task['done'], task_id))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ======================== عادت‌ها ========================

@app.route('/add_habit', methods=['POST'])
def add_habit():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('INSERT INTO habits (user_id, name, emoji, color, frequency) VALUES (?, ?, ?, ?, ?)',
                 (session['user_id'], request.form['name'], request.form.get('emoji', '🔥'),
                  request.form.get('color', '#4A90D9'), request.form.get('frequency', 'daily')))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/toggle_habit/<int:habit_id>')
def toggle_habit(habit_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    today = date.today().isoformat()
    conn = get_db()
    log = conn.execute('SELECT * FROM habit_logs WHERE habit_id = ? AND date = ?', (habit_id, today)).fetchone()
    if log:
        conn.execute('DELETE FROM habit_logs WHERE habit_id = ? AND date = ?', (habit_id, today))
    else:
        conn.execute('INSERT INTO habit_logs (habit_id, date) VALUES (?, ?)', (habit_id, today))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete_habit/<int:habit_id>')
def delete_habit(habit_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('DELETE FROM habits WHERE id = ? AND user_id = ?', (habit_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ======================== مالی ========================

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('INSERT INTO transactions (user_id, date, amount, type, category, description) VALUES (?, ?, ?, ?, ?, ?)',
                 (session['user_id'], request.form['date'], int(request.form['amount']),
                  request.form['type'], request.form['category'], request.form.get('description', '')))
    conn.commit()
    conn.close()
    return redirect(url_for('finance'))

@app.route('/delete_transaction/<int:trans_id>')
def delete_transaction(trans_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (trans_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('finance'))

# ======================== صفحات نمایش ========================

@app.route('/planner')
def planner():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    today = date.today().isoformat()
    conn = get_db()
    tasks = conn.execute('SELECT * FROM tasks WHERE user_id = ? AND date = ?', (session['user_id'], today)).fetchall()
    conn.close()
    return render_template('planner.html', tasks=tasks, today=today)

@app.route('/finance')
def finance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    transactions = conn.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC LIMIT 50', (session['user_id'],)).fetchall()
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    categories = {}
    for t in transactions:
        if t['type'] == 'expense':
            categories[t['category']] = categories.get(t['category'], 0) + t['amount']
    conn.close()
    return render_template('finance.html',
                         transactions=transactions,
                         total_income=total_income,
                         total_expense=total_expense,
                         balance=total_income - total_expense,
                         categories=categories,
                         today=date.today().isoformat())

@app.route('/habits')
def habits_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    habits = conn.execute('SELECT * FROM habits WHERE user_id = ?', (session['user_id'],)).fetchall()
    today = date.today().isoformat()
    for h in habits:
        logs = conn.execute('SELECT * FROM habit_logs WHERE habit_id = ?', (h['id'],)).fetchall()
        h['total_days'] = len(logs)
        h['last_7'] = sum(1 for l in logs if l['date'] >= date.today().isoformat())
        h['today_done'] = any(l['date'] == today for l in logs)
    conn.close()
    return render_template('habits.html', habits=habits, today=today)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)