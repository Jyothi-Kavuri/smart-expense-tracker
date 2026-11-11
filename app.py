
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
import sqlite3
import csv
import io
from datetime import date

app = Flask(__name__)
app.secret_key = "smart_expense_tracker_secret"

DATABASE = "expenses.db"


# DATABASE CONNECTION
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# CREATE TABLES
def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            expense_date TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            setting_key TEXT PRIMARY KEY,
            setting_value REAL NOT NULL
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO settings VALUES ('income', 0)
    """)

    conn.execute("""
        INSERT OR IGNORE INTO settings VALUES ('budget', 0)
    """)

    conn.commit()
    conn.close()


# GET SETTINGS
def get_setting(key):
    conn = get_db()
    result = conn.execute(
        "SELECT setting_value FROM settings WHERE setting_key=?",
        (key,)
    ).fetchone()
    conn.close()
    return float(result["setting_value"]) if result else 0


# SAVE SETTINGS
def save_setting(key, value):
    conn = get_db()
    conn.execute("""
        INSERT INTO settings (setting_key, setting_value)
        VALUES (?, ?)
        ON CONFLICT(setting_key)
        DO UPDATE SET setting_value=excluded.setting_value
    """, (key, value))
    conn.commit()
    conn.close()


# DASHBOARD
@app.route("/")
def home():

    today = date.today()
    month = today.strftime("%Y-%m")

    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    conn = get_db()

    income = get_setting("income")
    budget = get_setting("budget")

    # Current month total
    result = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE strftime('%Y-%m', expense_date)=?
    """, (month,)).fetchone()

    total = float(result["total"])
    balance = income - total

    # Expense history and date filtering
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if start_date:
        query += " AND expense_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND expense_date <= ?"
        params.append(end_date)

    query += " ORDER BY expense_date DESC, id DESC"

    expenses = conn.execute(query, params).fetchall()

    # Category-wise chart for current month
    category_data = conn.execute("""
        SELECT category, SUM(amount) AS amount
        FROM expenses
        WHERE strftime('%Y-%m', expense_date)=?
        GROUP BY category
    """, (month,)).fetchall()

    # Daily chart for current month
    daily_data = conn.execute("""
        SELECT expense_date, SUM(amount) AS amount
        FROM expenses
        WHERE strftime('%Y-%m', expense_date)=?
        GROUP BY expense_date
        ORDER BY expense_date
    """, (month,)).fetchall()

    conn.close()

    progress = min((total / budget) * 100, 100) if budget > 0 else 0

    categories = [row["category"] for row in category_data]
    category_amounts = [float(row["amount"]) for row in category_data]

    dates = [row["expense_date"] for row in daily_data]
    daily_amounts = [float(row["amount"]) for row in daily_data]

    return render_template(
        "index.html",
        income=income,
        total=total,
        balance=balance,
        budget=budget,
        progress=progress,
        expenses=expenses,
        categories=categories,
        category_amounts=category_amounts,
        dates=dates,
        daily_amounts=daily_amounts,
        start_date=start_date,
        end_date=end_date
    )


# SET INCOME
@app.route("/set-income", methods=["POST"])
def set_income():
    try:
        income = float(request.form.get("income", 0))

        if income <= 0:
            flash("Enter a valid income amount.")
        else:
            save_setting("income", income)
            flash("Income saved successfully!")

    except ValueError:
        flash("Invalid income amount.")

    return redirect(url_for("home"))


# SET BUDGET
@app.route("/set-budget", methods=["POST"])
def set_budget():
    try:
        budget = float(request.form.get("budget", 0))

        if budget <= 0:
            flash("Enter a valid budget.")
        else:
            save_setting("budget", budget)
            flash("Budget saved successfully!")

    except ValueError:
        flash("Invalid budget amount.")

    return redirect(url_for("home"))


# ADD EXPENSE
@app.route("/add", methods=["POST"])
def add():

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    expense_date = request.form.get("expense_date") or date.today().isoformat()

    try:
        amount = float(request.form.get("amount", 0))

        if not name or not category or amount <= 0:
            flash("Please enter valid expense details.")
            return redirect(url_for("home"))

        date.fromisoformat(expense_date)

        conn = get_db()
        conn.execute("""
            INSERT INTO expenses
            (name, amount, category, expense_date)
            VALUES (?, ?, ?, ?)
        """, (name, amount, category, expense_date))

        conn.commit()
        conn.close()

        flash("Expense added successfully!")

    except ValueError:
        flash("Please enter valid expense details.")

    return redirect(url_for("home"))


# EDIT EXPENSE
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    conn = get_db()
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id=?",
        (id,)
    ).fetchone()

    if expense is None:
        conn.close()
        return "Expense not found", 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()

        try:
            amount = float(request.form.get("amount", 0))

            if not name or not category or amount <= 0:
                flash("Enter valid details.")
                conn.close()
                return redirect(url_for("edit", id=id))

            conn.execute("""
                UPDATE expenses
                SET name=?, amount=?, category=?
                WHERE id=?
            """, (name, amount, category, id))

            conn.commit()
            conn.close()

            flash("Expense updated successfully!")
            return redirect(url_for("home"))

        except ValueError:
            conn.close()
            flash("Invalid amount.")
            return redirect(url_for("edit", id=id))

    conn.close()
    return render_template("edit.html", expense=expense)


# DELETE EXPENSE
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):

    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Expense deleted successfully!")
    return redirect(url_for("home"))


# EXPORT CSV
@app.route("/export")
def export():

    conn = get_db()

    expenses = conn.execute("""
        SELECT name, amount, category, expense_date
        FROM expenses
        ORDER BY expense_date DESC
    """).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Name", "Amount", "Category", "Date"])

    for expense in expenses:
        writer.writerow([
            expense["name"],
            expense["amount"],
            expense["category"],
            expense["expense_date"]
        ])

    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=expenses.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"

    return response


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
