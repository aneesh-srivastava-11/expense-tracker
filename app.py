import os
from flask import Flask, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "devkey")  # fallback for local dev
bcrypt = Bcrypt(app)

# ---- DB Connection ----
db_user = os.environ.get("DB_USER", "root")
db_password = os.environ.get("DB_PASSWORD", "root")
db_host = os.environ.get("DB_HOST", "localhost")
db_name = os.environ.get("DB_NAME", "tracker")

conn = mysql.connector.connect(
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)
cursor = conn.cursor(dictionary=True)

# ---- AUTH ROUTES ----
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s,%s)",
                (username, password)
            )
            conn.commit()
            return redirect('/login')
        except:
            return "Username already exists!"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        else:
            return "Invalid Credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---- EXPENSE ROUTES ----
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    cursor.execute(
        "SELECT * FROM expenses WHERE user_id=%s ORDER BY date DESC", (user_id,)
    )
    expenses = cursor.fetchall()
    total = sum(float(e['amount']) for e in expenses)

    # Prepare data for chart
    cursor.execute(
        "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id=%s GROUP BY category", (user_id,)
    )
    chart_data = cursor.fetchall()
    categories = [row['category'] or "Other" for row in chart_data]
    totals = [float(row['total']) for row in chart_data]

    return render_template(
        'index.html', expenses=expenses, total=total,
        categories=categories, totals=totals
    )

@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category'] or "Other"
        amount = float(request.form['amount'])
        date = request.form['date'] or datetime.now().strftime('%Y-%m-%d')
        user_id = session['user_id']

        cursor.execute(
            "INSERT INTO expenses (title, category, amount, date, user_id) VALUES (%s,%s,%s,%s,%s)",
            (title, category, amount, date, user_id)
        )
        conn.commit()
        return redirect('/')
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category'] or "Other"
        amount = float(request.form['amount'])
        date = request.form['date']

        cursor.execute(
            "UPDATE expenses SET title=%s, category=%s, amount=%s, date=%s WHERE id=%s AND user_id=%s",
            (title, category, amount, date, id, user_id)
        )
        conn.commit()
        return redirect('/')

    cursor.execute("SELECT * FROM expenses WHERE id=%s AND user_id=%s", (id, user_id))
    expense = cursor.fetchone()
    return render_template('edit.html', expense=expense)

@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    cursor.execute("DELETE FROM expenses WHERE id=%s AND user_id=%s", (id, user_id))
    conn.commit()
    return redirect('/')

# ---- REPORTS ROUTE ----
@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Total per category
    cursor.execute(
        "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id=%s GROUP BY category", (user_id,)
    )
    category_data = cursor.fetchall()
    for row in category_data:
        row['total'] = float(row['total'])

    # Total per month
    cursor.execute("""
        SELECT DATE_FORMAT(date, '%Y-%m') AS month, SUM(amount) AS total
        FROM expenses
        WHERE user_id=%s
        GROUP BY month
        ORDER BY month
    """, (user_id,))
    month_data = cursor.fetchall()
    for row in month_data:
        row['total'] = float(row['total'])

    # Overall total
    cursor.execute("SELECT SUM(amount) AS total FROM expenses WHERE user_id=%s", (user_id,))
    overall_total = cursor.fetchone()['total'] or 0

    return render_template(
        'reports.html', category_data=category_data, month_data=month_data, overall_total=overall_total
    )

if __name__ == '__main__':
    app.run(debug=True)
