# Import necessary libraries
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
import sqlite3
import matplotlib.pyplot as plt
import io
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import numpy as np

# Initialize the Flask application
app = Flask(__name__)
DATABASE = 'budget.db'  # Database file location

def get_db():
    """Establish and return a connection to the SQLite database with rows as dictionaries."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

def init_db():
    """Initialize the database tables and prepopulate some data."""
    db = get_db()  # Obtain a database connection
    with db:
        # Execute SQL to create categories table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        # Execute SQL to create expenses table if it doesn't exist with a date column
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
        # Insert default values into the categories table if they are not already present
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Food')")
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Utilities')")
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Entertainment')")
        db.commit()

@app.route('/')
def home():
    """Route to display all expenses with their categories on the homepage."""
    db = get_db()
    expenses = db.execute("SELECT expenses.*, categories.name AS category_name FROM expenses JOIN categories ON expenses.category_id = categories.id").fetchall()
    categories = db.execute("SELECT * FROM categories").fetchall()  # Ensure this line is fetching categories
    return render_template('index.html', expenses=expenses,categories=categories)

@app.route('/add', methods=['POST'])
def add_expense():
    """Route to handle the addition of new expenses through the web form."""
    db = get_db()
    name = request.form['name']
    amount = request.form['amount']
    category_id = request.form.get('category_id')
    date = request.form.get('date')
    # Insert the new expense record into the database if all fields are provided
    if name and amount and category_id and date:
        db.execute("INSERT INTO expenses (name, amount, category_id, date) VALUES (?, ?, ?, ?)",
                   (name, amount, category_id, date))
        db.commit()
    return redirect(url_for('home'))

@app.route('/expense_chart')
def expense_chart():
    """Route to generate a pie chart displaying expenses grouped by category."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT categories.name, SUM(expenses.amount) AS total FROM expenses JOIN categories ON expenses.category_id = categories.id GROUP BY categories.name")
    results = cursor.fetchall()
    if not results:
        return jsonify({"error": "No data available for chart."}), 404
    labels = [result['name'] for result in results]  # List of category names
    sizes = [result['total'] for result in results]  # Corresponding totals of expenses
    fig, ax = plt.subplots()  # Create a figure and a set of subplots
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)  # Create a pie chart
    ax.axis('equal')  # Equal aspect ratio ensures that the pie is drawn as a circle
    buf = io.BytesIO()  # Create a buffer to hold the image
    plt.savefig(buf, format='png')  # Save the pie chart as a PNG image to the buffer
    buf.seek(0)  # Seek to the start of the stream
    return send_file(buf, mimetype='image/png')  # Return the image as a response

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Route to handle searching of expenses by category and/or date range."""
    db = get_db()
    query = "SELECT * FROM expenses WHERE 1=1"  # SQL query starting point
    params = []  # Parameters for the SQL query
    data_source = request.form if request.method == 'POST' else request.args
    category_id = data_source.get('category_id')
    if category_id:
        query += " AND category_id = ?"  # Append category condition to the query
        params.append(int(category_id))
    start_date = data_source.get('start_date')
    if start_date:
        query += " AND date >= ?"  # Append start date condition to the query
        params.append(start_date)
    end_date = data_source.get('end_date')
    if end_date:
        query += " AND date <= ?"  # Append end date condition to the query
        params.append(end_date)
    expenses = db.execute(query, params).fetchall()  # Execute the query and fetch results
    categories = db.execute("SELECT * FROM categories").fetchall()
    return render_template('search.html', expenses=expenses,categories = categories)  # Render the search results page

# Additional Pandas and Scikit-Learn integration here, with detailed comments:
@app.route('/monthly_summary')
def monthly_summary():
    db = get_db()
    query = "SELECT date, amount, category_id FROM expenses"
    df = pd.read_sql_query(query, db)  # Load data into a Pandas DataFrame
    df['date'] = pd.to_datetime(df['date'])  # Convert date column to datetime type for easier manipulation

    # Group expenses by month and category, and sum the amounts
    summary = df.groupby([df['date'].dt.to_period('M'), 'category_id'])['amount'].sum().unstack(fill_value=0)

    # Convert Period index (which is not JSON serializable) to string
    summary.index = summary.index.astype(str)  # Convert Periods to string

    return jsonify(summary.to_dict())  # Return the summary as JSON


@app.route('/forecast_expenses', methods=['GET'])
def forecast_expenses():
    """Route to predict future expenses using a simple linear regression model."""
    db = get_db()
    query = "SELECT date, amount FROM expenses"
    df = pd.read_sql_query(query, db)  # Load expenses into DataFrame
    df['date'] = pd.to_datetime(df['date'])  # Ensure 'date' column is datetime type
    
    # Provide a default date for NaT values
    default_date = pd.Timestamp('today')  # Use today's date or any other appropriate default
    df['date'] = df['date'].fillna(default_date)
    
    df['date_ordinal'] = df['date'].apply(lambda x: x.toordinal())  # Convert dates to ordinal for model training
    model = LinearRegression()  # Initialize the Linear Regression model
    model.fit(df[['date_ordinal']], df['amount'])  # Fit the model
    future_dates = pd.date_range('2024-07-01', periods=3, freq='M')  # Generate future dates for prediction
    future_ordinals = np.array([date.toordinal() for date in future_dates]).reshape(-1, 1)  # Convert future dates to ordinals
    predictions = model.predict(future_ordinals)  # Predict expenses for future dates
    
     # Prepare data for JSON serialization
    response_data = {
        'date': [date.strftime('%Y-%m-%d') for date in future_dates],
        'prediction': predictions.tolist()
    }

    return jsonify(response_data)

if __name__ == '__main__':
    init_db()  # Ensure the database is initialized
    app.run(debug=True)  # Start the Flask app in debug mode for development purposes
