# Import necessary libraries
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
import sqlite3
import matplotlib.pyplot as plt
import io

# Initialize the Flask application
app = Flask(__name__)
DATABASE = 'budget.db'

def get_db():
    # Establish a connection to the specified SQLite database
    conn = sqlite3.connect(DATABASE)
    # Configure the connection to return rows as dictionaries to access columns by names
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Initialize the database with predefined tables and data
    db = get_db()
    with db:
        # Create categories table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        # Create expenses table if it doesn't exist with a new 'date' column
        db.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                category_id INTEGER,
                date DATE,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        # Prepopulate the categories table with default values if not already present
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Food')")
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Utilities')")
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Entertainment')")
        db.commit()

@app.route('/')
def home():
    # Route to display all expenses with their categories
    db = get_db()
    expenses = db.execute("SELECT expenses.*, categories.name AS category_name FROM expenses JOIN categories ON expenses.category_id = categories.id").fetchall()
    categories = db.execute("SELECT * FROM categories").fetchall()
    return render_template('index.html', expenses=expenses, categories=categories)

@app.route('/add', methods=['POST'])
def add_expense():
    # Route to add a new expense to the database
    db = get_db()
    name = request.form['name']
    amount = request.form['amount']
    category_id = request.form.get('category_id')
    date = request.form.get('date')  # Retrieve date from form
    if category_id and date:
        db.execute("INSERT INTO expenses (name, amount, category_id, date) VALUES (?, ?, ?, ?)", (name, amount, category_id, date))
    db.commit()
    return redirect(url_for('home'))

@app.route('/expense_chart')
def expense_chart():
    # Route to generate a pie chart of expenses by category
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT categories.name, SUM(expenses.amount) AS total FROM expenses JOIN categories ON expenses.category_id = categories.id GROUP BY categories.name")
        results = cursor.fetchall()

        if not results:
            return jsonify({"error": "No data available for chart."}), 404

        labels = [i['name'] for i in results]
        sizes = [i['total'] for i in results]

        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        return send_file(buf, mimetype='image/png')
    except Exception as e:
        return str(e), 500

@app.route('/search', methods=['GET', 'POST'])
def search():
    # Route to handle searching expenses based on category and date
    db = get_db()
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    
    # Choose data source based on the method: form data for POST, query string for GET
    data_source = request.form if request.method == 'POST' else request.args

    category_id = data_source.get('category_id')
    if category_id:
        query += " AND category_id = ?"
        params.append(int(category_id))

    start_date = data_source.get('start_date')
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    end_date = data_source.get('end_date')
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    expenses = db.execute(query, params).fetchall()
    categories = db.execute("SELECT * FROM categories").fetchall()
    return render_template('search.html', expenses=expenses, categories=categories)

if __name__ == '__main__':
    # Initialize the database and start the Flask application in debug mode
    init_db()
    app.run(debug=True)
