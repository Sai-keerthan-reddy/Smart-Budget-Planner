from flask import Flask, request,render_template
import sqlite3

app = Flask(__name__)
DATABASE = 'budget.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       amount REAL NOT NULL)''')
        db.commit()

@app.route('/')
def home():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM expenses")
    expenses = cursor.fetchall()
    return render_template('index.html',expenses=expenses)

@app.route('/add',methods =['POST'])
def add_expense():
    db = get_db()
    cursor = db.cursor()
    name = request.form['name']
    amount = request.form['amount']
    cursor.execute("INSERT INTO expenses (name, amount) VALUES (?, ?)",(name,amount))
    db.commit()
    return "Expense added!"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)