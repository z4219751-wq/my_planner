from flask import Flask, render_template, request, redirect, url_for
from datetime import date
import os
from supabase import create_client, Client

app = Flask(name)

# ====== اتصال به Supabase ======
SUPABASE_URL = "https://yibdkjpgutekdmpjwocf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlpYmRranBndXRla2RtcGp3b2NmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgzODE1MjgsImV4cCI6MjEwMzk1NzUyOH0.gZlFrB7UE6sfd90IL24mLfnghWC-Pp3c7rLftltl7iA"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ====== صفحه اصلی ======
@app.route('/')
def index():
    today = date.today().isoformat()
    
    tasks_response = supabase.table('tasks').select('*').eq('date', today).execute()
    tasks = tasks_response.data
    tasks_count = len(tasks)
    done_count = sum(1 for t in tasks if t.get('done', False))
    completion = int((done_count / tasks_count * 100)) if tasks_count > 0 else 0
    
    expense_response = supabase.table('transactions').select('*').eq('date', today).eq('type', 'expense').execute()
    today_expense = sum(t['amount'] for t in expense_response.data)
    
    habits_response = supabase.table('habits').select('*').execute()
    habits = habits_response.data
    habit_progress = []
    for h in habits:
        log_response = supabase.table('habit_logs').select('*').eq('habit_id', h['id']).eq('date', today).execute()
        habit_progress.append({
            'id': h['id'],
            'name': h['name'],
            'emoji': h.get('emoji', '🔥'),
            'color': h.get('color', '#7C3AED'),
            'done': len(log_response.data) > 0
        })
    
    return render_template('index.html',
                         users=3000,
                         tasks=tasks,
                         tasks_count=tasks_count,
                         done_count=done_count,
                         completion=completion,
                         today_expense=today_expense,
                         habits=habit_progress,
                         today=today,
                         total_habits=len(habits),
                         done_habits=sum(1 for h in habit_progress if h['done']))

# ====== وظایف ======
@app.route('/add_task', methods=['POST'])
def add_task():
    new_task = {
        'title': request.form['title'],
        'date': request.form['date'],
        'priority': int(request.form.get('priority', 3)),
        'done': False,
        'category': request.form.get('category', 'شخصی')
    }
    supabase.table('tasks').insert(new_task).execute()
    return redirect(url_for('index'))

@app.route('/toggle_task/<int:task_id>')
def toggle_task(task_id):
    task = supabase.table('tasks').select('*').eq('id', task_id).execute()
    if task.data:
        current = task.data[0]
        supabase.table('tasks').update({'done': not current['done']}).eq('id', task_id).execute()
    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    supabase.table('tasks').delete().eq('id', task_id).execute()
    return redirect(url_for('index'))

# ====== عادت‌ها ======
@app.route('/add_habit', methods=['POST'])
def add_habit():
    new_habit = {
        'name': request.form['name'],
        'emoji': request.form.get('emoji', '🔥'),
        'color': request.form.get('color', '#7C3AED'),
        'frequency': request.form.get('frequency', 'daily')
    }
    supabase.table('habits').insert(new_habit).execute()
    return redirect(url_for('index'))

@app.route('/toggle_habit/<int:habit_id>')
def toggle_habit(habit_id):
    today = date.today().isoformat()
    existing = supabase.table('habit_logs').select('*').eq('habit_id', habit_id).eq('date', today).execute()
    if existing.data:
        supabase.table('habit_logs').delete().eq('habit_id', habit_id).eq('date', today).execute()
    else:
        supabase.table('habit_logs').insert({'habit_id': habit_id, 'date': today}).execute()
    return redirect(url_for('index'))
@app.route('/delete_habit/<int:habit_id>')
def delete_habit(habit_id):
    supabase.table('habit_logs').delete().eq('habit_id', habit_id).execute()
    supabase.table('habits').delete().eq('id', habit_id).execute()
    return redirect(url_for('index'))

# ====== مالی ======
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    new_trans = {
        'date': request.form['date'],
        'amount': int(request.form['amount']),
        'type': request.form['type'],
        'category': request.form['category'],
        'description': request.form.get('description', '')
    }
    supabase.table('transactions').insert(new_trans).execute()
    return redirect(url_for('finance'))

@app.route('/delete_transaction/<int:trans_id>')
def delete_transaction(trans_id):
    supabase.table('transactions').delete().eq('id', trans_id).execute()
    return redirect(url_for('finance'))

# ====== صفحات ======
@app.route('/planner')
def planner():
    today = date.today().isoformat()
    tasks = supabase.table('tasks').select('*').eq('date', today).execute()
    return render_template('planner.html', tasks=tasks.data, today=today)

@app.route('/finance')
def finance():
    trans = supabase.table('transactions').select('*').order('date', desc=True).limit(50).execute()
    transactions = trans.data
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    categories = {}
    for t in transactions:
        if t['type'] == 'expense':
            categories[t['category']] = categories.get(t['category'], 0) + t['amount']
    return render_template('finance.html',
                         transactions=transactions,
                         total_income=total_income,
                         total_expense=total_expense,
                         balance=total_income - total_expense,
                         categories=categories,
                         today=date.today().isoformat())

@app.route('/habits')
def habits_page():
    habits = supabase.table('habits').select('*').execute().data
    today = date.today().isoformat()
    for h in habits:
        logs = supabase.table('habit_logs').select('*').eq('habit_id', h['id']).execute().data
        h['total_days'] = len(logs)
        h['last_7'] = sum(1 for l in logs if l.get('date', '') >= date.today().isoformat())
        h['today_done'] = any(l.get('date') == today for l in logs)
    return render_template('habits.html', habits=habits, today=today)

if name == 'main':
    app.run(host='0.0.0.0', port=10000)