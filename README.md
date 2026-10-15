# Mini Banking System - Oracle PL/SQL + Flask web app

A small bank application. All banking rules live in the PL/SQL package `bank_pkg`;
the Flask web app is only the front end that calls it.

## Features
- Dashboard with totals and all accounts
- Add customers, open SAVINGS / CURRENT accounts
- Deposit, withdraw, transfer (transfer is atomic), recent-transactions statement, close account
- Rules (enforced in PL/SQL): SAVINGS minimum balance 500, no overdraft, closed accounts blocked,
  close only at zero balance, transaction history cannot be edited/deleted (trigger)

## Setup (once)
1. Oracle Database (e.g. Oracle XE) running. Create a schema:
   run `sql/00_create_user.sql` as SYSTEM (connected to XEPDB1), or use your own user.
2. Connect as that user and run: `@install.sql`  (creates tables, package, 3 sample accounts)
3. Python 3.9+:
   ```
   python -m venv venv
   venv\Scripts\activate          (Windows)   |   source venv/bin/activate   (Linux/Mac)
   pip install -r requirements.txt
   ```
4. Set connection details if yours differ (defaults shown):
   ```
   BANK_USER=bank  BANK_PASSWORD=bank123  BANK_DSN=localhost:1521/XEPDB1
   ```
   Windows: `set BANK_PASSWORD=...`   Linux/Mac: `export BANK_PASSWORD=...`

## Run
```
python app.py
```
Open http://127.0.0.1:5000

## Project structure
```
app.py            Flask routes
db.py             Oracle connection + calls to bank_pkg
templates/        HTML pages (Jinja)
static/style.css  styling
sql/              tables, package, sample data
tests/            web-layer tests (python tests/test_app.py, no Oracle needed)
```

## Things to try (good for demo / viva)
- Withdraw too much from a SAVINGS account -> blocked by minimum balance
- Transfer to the same account / a missing account -> error shown
- Close an account that still has money -> error
- In SQL: `DELETE FROM transactions;` -> blocked by trigger
