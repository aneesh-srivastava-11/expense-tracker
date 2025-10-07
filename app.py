import os
from flask import Flask, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId

# ---- Load environment variables ----
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "devkey")
bcrypt = Bcrypt(app)

# ---- MongoDB Connection ----
mongo_uri = os.environ.get("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["tracker"]  # explicitly select your DB
users_col = db['users']
expenses_col = db['expenses']

# ---- AUTH ROUTES ----
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        if users_col.find_one({"username": username}):
            return "Username already exists!"
        users_col.insert_one({"username": username, "password": password})
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users_col.find_one({"username": username})
        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = str(user["_id"])
            session['username'] = user["username"]
            return redirect('/')
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
    expenses = list(expenses_col.find({"user_id": user_id}).sort("date", -1))
    total = sum(float(e['amount']) for e in expenses)

    # Category totals for chart
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}
    ]
    chart_data = list(expenses_col.aggregate(pipeline))
    categories = [row["_id"] or "Other" for row in chart_data]
    totals = [float(row["total"]) for row in chart_data]

    return render_template('index.html', expenses=expenses, total=total,
                           categories=categories, totals=totals)

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

        expenses_col.insert_one({
            "title": title,
            "category": category,
            "amount": amount,
            "date": date,
            "user_id": user_id
        })
        return redirect('/')
    return render_template('add.html')

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    if 'user_id' not in session:
        return redirect('/login')

    expense = expenses_col.find_one({"_id": ObjectId(id), "user_id": session['user_id']})
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category'] or "Other"
        amount = float(request.form['amount'])
        date = request.form['date']

        expenses_col.update_one(
            {"_id": ObjectId(id), "user_id": session['user_id']},
            {"$set": {"title": title, "category": category, "amount": amount, "date": date}}
        )
        return redirect('/')
    return render_template('edit.html', expense=expense)

@app.route('/delete/<id>')
def delete(id):
    if 'user_id' not in session:
        return redirect('/login')

    expenses_col.delete_one({"_id": ObjectId(id), "user_id": session['user_id']})
    return redirect('/')

# ---- REPORTS ----
@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Category-wise totals
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}
    ]
    category_data = list(expenses_col.aggregate(pipeline))
    for row in category_data:
        row['total'] = float(row['total'])

    # Monthly totals
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": {"$substr": ["$date", 0, 7]}, "total": {"$sum": "$amount"}}},
        {"$sort": {"_id": 1}}
    ]
    month_data = list(expenses_col.aggregate(pipeline))
    for row in month_data:
        row['total'] = float(row['total'])

    overall_total = sum(e['total'] for e in category_data) if category_data else 0

    return render_template('reports.html', category_data=category_data,
                           month_data=month_data, overall_total=overall_total)


# ---- Run App ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
