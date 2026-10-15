"""Mini Banking System - Flask front end for the PL/SQL package bank_pkg.
Run:  python app.py   then open http://127.0.0.1:5000"""
import os
from decimal import Decimal, InvalidOperation

from flask import Flask, abort, flash, redirect, render_template, request, url_for

import db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")


@app.template_filter("money")
def money(value):
    return "{:,.2f}".format(value or 0)


@app.template_filter("dt")
def fmt_date(value):
    return value.strftime("%d-%b-%Y %H:%M") if value else ""


def parse_amount(raw):
    try:
        amt = Decimal((raw or "").strip())
    except InvalidOperation:
        raise db.BankError("Enter a valid amount.")
    if amt <= 0 or amt.as_tuple().exponent < -2 or amt >= Decimal("10000000000"):
        raise db.BankError("Amount must be positive, with at most 2 decimal places.")
    return amt


def parse_int(raw, label):
    try:
        return int((raw or "").strip())
    except ValueError:
        raise db.BankError(f"{label} must be a number.")


def attempt(action, success, target):
    """Run a database action, flash the outcome, then redirect."""
    try:
        result = action()
        flash(success(result) if callable(success) else success, "ok")
    except db.BankError as e:
        flash(str(e), "error")
    return redirect(target)


@app.route("/")
def index():
    try:
        return render_template("index.html", stats=db.stats(), accounts=db.list_accounts())
    except db.BankError as e:
        flash(str(e), "error")
        return render_template("index.html", stats=None, accounts=[])


@app.route("/customers", methods=["GET", "POST"])
def customers():
    if request.method == "POST":
        f = request.form
        return attempt(lambda: db.add_customer(f.get("name", "").strip(), f.get("phone", "").strip(),
                                               f.get("email", "").strip()),
                       lambda cid: f"Customer created with ID {cid}.", url_for("customers"))
    try:
        rows = db.list_customers()
    except db.BankError as e:
        flash(str(e), "error")
        rows = []
    return render_template("customers.html", customers=rows)


@app.route("/accounts/new", methods=["GET", "POST"])
def open_account():
    if request.method == "POST":
        f = request.form
        try:
            cust = parse_int(f.get("cust_id"), "Customer ID")
            initial = Decimal(f.get("initial") or "0") if f.get("initial", "").strip() else Decimal("0")
            if initial < 0:
                raise db.BankError("Opening deposit cannot be negative.")
            acc = db.open_account(cust, f.get("acc_type", ""), initial)
        except InvalidOperation:
            flash("Enter a valid opening deposit.", "error")
        except db.BankError as e:
            flash(str(e), "error")
        else:
            flash(f"Account {acc} opened.", "ok")
            return redirect(url_for("account", acc_no=acc))
    return render_template("open_account.html", min_balance=500)


@app.route("/accounts/<int:acc_no>")
def account(acc_no):
    try:
        acc = db.get_account(acc_no)
        txns = db.get_transactions(acc_no) if acc else []
    except db.BankError as e:
        flash(str(e), "error")
        return redirect(url_for("index"))
    if not acc:
        abort(404)
    return render_template("account.html", acc=acc, txns=txns)


@app.route("/accounts/<int:acc_no>/deposit", methods=["POST"])
def deposit(acc_no):
    def go():
        amt = parse_amount(request.form.get("amount"))
        db.deposit(acc_no, amt)
        return amt
    return attempt(go, lambda a: f"Deposited {money(a)}.", url_for("account", acc_no=acc_no))


@app.route("/accounts/<int:acc_no>/withdraw", methods=["POST"])
def withdraw(acc_no):
    def go():
        amt = parse_amount(request.form.get("amount"))
        db.withdraw(acc_no, amt)
        return amt
    return attempt(go, lambda a: f"Withdrew {money(a)}.", url_for("account", acc_no=acc_no))


@app.route("/accounts/<int:acc_no>/transfer", methods=["POST"])
def transfer(acc_no):
    def go():
        to = parse_int(request.form.get("to_acc"), "Destination account")
        amt = parse_amount(request.form.get("amount"))
        db.transfer(acc_no, to, amt)
        return to, amt
    return attempt(go, lambda r: f"Transferred {money(r[1])} to account {r[0]}.",
                   url_for("account", acc_no=acc_no))


@app.route("/accounts/<int:acc_no>/close", methods=["POST"])
def close(acc_no):
    return attempt(lambda: db.close_account(acc_no), "Account closed.", url_for("account", acc_no=acc_no))


if __name__ == "__main__":
    app.run(debug=True)
