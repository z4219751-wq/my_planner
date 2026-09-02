from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import date

app = Flask(__name__)
DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'tasks': [],
        'transactions': [],
        'habits': [],
        'habit_logs': [],
        'users': 2847
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    data = load_data()
    today = date.today().isoformat()
    today_tasks = [t for t in data['tasks'] if t.get('date') == today]
    tasks_count = len(today_tasks)
    done_count = sum(1 for t in today_tasks if t.get('done', False))
    completion = int((done_count / tasks_count * 100)) if tasks_count > 0 else 0
    today_expense = sum(t['amount'] for t in data['transactions'] if t.get('date') == today and t.get('type') == 'expense')
    habits = data['habits']
    habit_progress = []
    for h in habits:
        logs = [l for l in data['habit_logs'] if l['habit_id'] == h['id'] and l.get('date') == today]
        habit_progress.append({
            'id': h['id'],
            'name': h['name'],
            'emoji': h.get('emoji', '🔥'),
            'color': h.get('color', '#7C3AED'),
            'done': len(logs) > 0
        })
    return render_template('index.html',
                         users=data['users'],
                         tasks=today_tasks,
                         tasks_count=tasks_count,
                         done_count=done_count,
                         completion=completion,
                         today_expense=today_expense,
                         habits=habit_progress,
                         today=today,
                         total_habits=len(habits),
                         done_habits=sum(1 for h in habit_progress if h['done']))

@app.route('/add_task', methods=['POST'])
def add_task():
    data = load_data()
    new_task = {
        'id': len(data['tasks']) + 1,
        'title': request.form['title'],
        'date': request.form['date'],
        'priority': int(request.form.get('priority', 3)),
        'done': False,
        'category': request.form.get('category', 'شخصی')
    }
    data['tasks'].append(new_task)
    save_data(data)
    return redirect(url_for('index'))

@app.route('/toggle_task/<int:task_id>')
def toggle_task(task_id):
    data = load_data()
    for task in data['tasks']:
        if task['id'] == task_id:
            task['done'] = not task.get('done', False)
            break
    save_data(data)
    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    data = load_data()
    data['tasks'] = [t for t in data['tasks'] if t['id'] != task_id]
    save_data(data)
    return redirect(url_for('index'))

@app.route('/add_habit', methods=['POST'])
def add_habit():
    data = load_data()
    new_habit = {
        'id': len(data['habits']) + 1,
        'name': request.form['name'],
        'emoji': request.form.get('emoji', '🔥'),
        'color': request.form.get('color', '#7C3AED'),
        'frequency': request.form.get('frequency', 'daily')
    }
    data['habits'].append(new_habit)
    save_data(data)
    return redirect(url_for('index'))

@app.route('/toggle_habit/<int:habit_id>')
def toggle_habit(habit_id):
    data = load_data()
    today = date.today().isoformat()
    existing = [l for l in data['habit_logs'] if l['habit_id'] == habit_id and l.get('date') == today]
    if existing:
        data['habit_logs'] = [l for l in data['habit_logs'] if not (l['habit_id'] == habit_id and l.get('date') == today)]
    else:
        data['habit_logs'].append({'habit_id': habit_id, 'date': today, 'done': True})
    save_data(data)
    return redirect(url_for('index'))
@app.route('/delete_habit/<int:habit_id>')
def delete_habit(habit_id):
    data = load_data()
    data['habits'] = [h for h in data['habits'] if h['id'] != habit_id]
    data['habit_logs'] = [l for l in data['habit_logs'] if l['habit_id'] != habit_id]
    save_data(data)
    return redirect(url_for('index'))

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    data = load_data()
    new_trans = {
        'id': len(data['transactions']) + 1,
        'date': request.form['date'],
        'amount': int(request.form['amount']),
        'type': request.form['type'],
        'category': request.form['category'],
        'description': request.form.get('description', '')
    }
    data['transactions'].append(new_trans)
    save_data(data)
    return redirect(url_for('finance'))

@app.route('/delete_transaction/<int:trans_id>')
def delete_transaction(trans_id):
    data = load_data()
    data['transactions'] = [t for t in data['transactions'] if t['id'] != trans_id]
    save_data(data)
    return redirect(url_for('finance'))

@app.route('/planner')
def planner():
    data = load_data()
    today = date.today().isoformat()
    tasks = [t for t in data['tasks'] if t.get('date') == today]
    return render_template('planner.html', tasks=tasks, today=today)

@app.route('/finance')
def finance():
    data = load_data()
    transactions = sorted(data['transactions'], key=lambda x: x['date'], reverse=True)
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    categories = {}
    for t in transactions:
        if t['type'] == 'expense':
            categories[t['category']] = categories.get(t['category'], 0) + t['amount']
    return render_template('finance.html',
                         transactions=transactions[:50],
                         total_income=total_income,
                         total_expense=total_expense,
                         balance=total_income - total_expense,
                         categories=categories,
                         today=date.today().isoformat())

@app.route('/habits')
def habits_page():
    data = load_data()
    habits = data['habits']
    today = date.today().isoformat()
    for h in habits:
        logs = [l for l in data['habit_logs'] if l['habit_id'] == h['id']]
        h['total_days'] = len(logs)
        h['last_7'] = sum(1 for l in logs if l.get('date', '') >= date.today().isoformat())
        h['today_done'] = any(l.get('date') == today for l in logs)
    return render_template('habits.html', habits=habits, today=today)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)