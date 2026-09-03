from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "mysecretkey123456789"

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
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
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
            color TEXT DEFAULT '#7C3AED',
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
    
    conn.commit()
    conn.close()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    today = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
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
    
    conn.close()
    
    return render_template('index.html',
                         tasks=tasks,
                         tasks_count=tasks_count,
                         done_count=done_count,
                         completion=completion,
                         today_expense=today_expense,
                         habits=habit_progress,
                         today=today,
                         total_habits=len(habits),
                         done_habits=sum(1 for h in habit_progress if h['done']))
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return "این ایمیل قبلاً ثبت شده است"
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['email'] = user['email']
            return redirect(url_for('index'))
        else:
            return "ایمیل یا رمز عبور اشتباه است"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

@app.route('/add_habit', methods=['POST'])
def add_habit():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('INSERT INTO habits (user_id, name, emoji, color, frequency) VALUES (?, ?, ?, ?, ?)',
                 (session['user_id'], request.form['name'], request.form.get('emoji', '🔥'),
                  request.form.get('color', '#7C3AED'), request.form.get('frequency', 'daily')))
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

if name == '__main__':
    app.run(host='0.0.0.0', port=10000)