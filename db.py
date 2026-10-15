"""Thin data layer: every banking rule lives in the PL/SQL package bank_pkg.
This file only connects to Oracle, calls the package, and runs a few SELECTs for display."""
import os
import re
from contextlib import contextmanager

import oracledb

DSN = os.environ.get("BANK_DSN", "localhost:1521/XEPDB1")
USER = os.environ.get("BANK_USER", "bank")
PASSWORD = os.environ.get("BANK_PASSWORD", "bank123")


class BankError(Exception):
    """A readable error message that is safe to show to the user."""


def _clean(err):
    text = str(err)
    m = re.search(r"ORA-200\d\d:\s*(.*)", text)      # errors raised by our PL/SQL package
    if m:
        return m.group(1).split("\nORA-")[0].strip()
    if "ORA-02290" in text:
        return "That value is not allowed by a database rule."
    return "Database problem: " + text.splitlines()[0]


@contextmanager
def _cursor():
    try:
        conn = oracledb.connect(user=USER, password=PASSWORD, dsn=DSN)
    except oracledb.Error as e:
        raise BankError(_clean(e))
    try:
        yield conn.cursor()
    except oracledb.Error as e:
        raise BankError(_clean(e))
    finally:
        conn.close()


def _rows(cur):
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------- reads ----------
def stats():
    with _cursor() as cur:
        cur.execute("SELECT COUNT(*), NVL(SUM(balance),0) FROM accounts WHERE status = 'ACTIVE'")
        accounts, total = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
    return {"accounts": accounts, "total": total, "customers": customers}


def list_accounts():
    with _cursor() as cur:
        cur.execute("""SELECT a.acc_no, c.name, a.acc_type, a.balance, a.status
                       FROM accounts a JOIN customers c ON c.cust_id = a.cust_id
                       ORDER BY a.acc_no""")
        return _rows(cur)


def list_customers():
    with _cursor() as cur:
        cur.execute("""SELECT c.cust_id, c.name, c.phone, c.email, c.created_on,
                              (SELECT COUNT(*) FROM accounts a WHERE a.cust_id = c.cust_id) AS accounts
                       FROM customers c ORDER BY c.cust_id""")
        return _rows(cur)


def get_account(acc_no):
    with _cursor() as cur:
        cur.execute("""SELECT a.acc_no, a.cust_id, c.name, c.phone, a.acc_type, a.balance,
                              a.status, a.opened_on
                       FROM accounts a JOIN customers c ON c.cust_id = a.cust_id
                       WHERE a.acc_no = :acc""", acc=acc_no)
        rows = _rows(cur)
    return rows[0] if rows else None


def get_transactions(acc_no, limit=20):
    with _cursor() as cur:
        cur.execute("""SELECT * FROM (
                         SELECT txn_id, txn_type, amount, balance_after, txn_date, remarks
                         FROM transactions WHERE acc_no = :acc ORDER BY txn_id DESC)
                       WHERE ROWNUM <= :n""", acc=acc_no, n=limit)
        return _rows(cur)


# ---------- writes (all go through the PL/SQL package) ----------
def add_customer(name, phone, email):
    with _cursor() as cur:
        return int(cur.callfunc("bank_pkg.add_customer", oracledb.NUMBER, [name, phone, email or None]))


def open_account(cust_id, acc_type, initial):
    with _cursor() as cur:
        return int(cur.callfunc("bank_pkg.open_account", oracledb.NUMBER, [cust_id, acc_type, initial]))


def deposit(acc_no, amount):
    with _cursor() as cur:
        cur.callproc("bank_pkg.deposit", [acc_no, amount])


def withdraw(acc_no, amount):
    with _cursor() as cur:
        cur.callproc("bank_pkg.withdraw", [acc_no, amount])


def transfer(from_acc, to_acc, amount):
    with _cursor() as cur:
        cur.callproc("bank_pkg.transfer", [from_acc, to_acc, amount])


def close_account(acc_no):
    with _cursor() as cur:
        cur.callproc("bank_pkg.close_account", [acc_no])
