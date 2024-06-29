from flask import Flask, request,jsonify,render_template,redirect,url_for,send_file
import sqlite3
import matplotlib.pyplot as plt
import io

app = Flask(__name__)
DATABASE = 'budget.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Make rows returned by the cursor as dictionary
    return conn

def init_db():
    db = get_db()
    with db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                category_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        # Prepopulate some categories
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Food')")
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Utilities')")
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Entertainment')")
        db.commit()

@app.route('/')
def home():
    db = get_db()
    expenses = db.execute("SELECT expenses.*, categories.name AS category_name FROM expenses JOIN categories ON expenses.category_id = categories.id").fetchall()
    categories = db.execute("SELECT * FROM categories").fetchall()
    return render_template('index.html', expenses=expenses, categories=categories)


@app.route('/add', methods=['POST'])
def add_expense():
    db = get_db()
    name = request.form['name']
    amount = request.form['amount']
    category_id = request.form.get('category_id')  # Get the category ID from form data
    if category_id:
        db.execute("INSERT INTO expenses (name, amount, category_id) VALUES (?, ?, ?)", (name, amount, category_id))
    else:
        db.execute("INSERT INTO expenses (name, amount) VALUES (?, ?)", (name, amount))
    db.commit()
    return redirect(url_for('home'))

@app.route('/expense_chart')
def expense_chart():
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)