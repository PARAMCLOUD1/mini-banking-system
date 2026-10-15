"""In-memory stand-in for db.py, used ONLY to test the web layer without Oracle.
It mirrors the rules in bank_pkg; it does not test the PL/SQL itself."""
import re
from datetime import datetime


class BankError(Exception):
    pass


MIN = 500
customers, accounts, txns = {}, {}, []


def reset():
    customers.clear(); accounts.clear(); txns.clear()


def _log(acc, typ, amt, rem):
    txns.append({"txn_id": len(txns) + 1, "acc_no": acc, "txn_type": typ, "amount": amt,
                 "balance_after": accounts[acc]["balance"], "txn_date": datetime.now(), "remarks": rem})


def _get(acc):
    if acc not in accounts:
        raise BankError(f"Account {acc} does not exist.")
    if accounts[acc]["status"] != "ACTIVE":
        raise BankError(f"Account {acc} is closed.")
    return accounts[acc]


def stats():
    act = [a for a in accounts.values() if a["status"] == "ACTIVE"]
    return {"accounts": len(act), "total": sum(a["balance"] for a in act), "customers": len(customers)}


def list_accounts():
    return [{"acc_no": a["acc_no"], "name": customers[a["cust_id"]]["name"], "acc_type": a["acc_type"],
             "balance": a["balance"], "status": a["status"]} for a in accounts.values()]


def list_customers():
    return [dict(c, accounts=sum(1 for a in accounts.values() if a["cust_id"] == c["cust_id"]))
            for c in customers.values()]


def get_account(n):
    a = accounts.get(n)
    return dict(a, name=customers[a["cust_id"]]["name"], phone=customers[a["cust_id"]]["phone"]) if a else None


def get_transactions(n, limit=20):
    return [t for t in reversed(txns) if t["acc_no"] == n][:limit]


def add_customer(name, phone, email):
    if not name or not re.fullmatch(r"[0-9]{10}", phone):
        raise BankError("Name is required and phone must be 10 digits.")
    cid = len(customers) + 1
    customers[cid] = {"cust_id": cid, "name": name, "phone": phone, "email": email, "created_on": datetime.now()}
    return cid


def open_account(cust, typ, initial):
    if cust not in customers:
        raise BankError(f"Customer {cust} does not exist.")
    typ = typ.upper()
    if typ not in ("SAVINGS", "CURRENT"):
        raise BankError("Account type must be SAVINGS or CURRENT.")
    if typ == "SAVINGS" and initial < MIN:
        raise BankError(f"SAVINGS needs an opening deposit of at least {MIN}")
    n = 1001 + len(accounts)
    accounts[n] = {"acc_no": n, "cust_id": cust, "acc_type": typ, "balance": 0, "status": "ACTIVE",
                   "opened_on": datetime.now()}
    if initial > 0:
        accounts[n]["balance"] += initial; _log(n, "OPENING", initial, "Opening deposit")
    return n


def deposit(n, amt):
    a = _get(n); a["balance"] += amt; _log(n, "DEPOSIT", amt, "Cash deposit")


def _withdraw(n, amt, typ, rem):
    a = _get(n)
    floor = MIN if a["acc_type"] == "SAVINGS" else 0
    if a["balance"] - amt < floor:
        raise BankError(f"Insufficient funds. Balance: {a['balance']}, minimum to maintain: {floor}")
    a["balance"] -= amt; _log(n, typ, amt, rem)


def withdraw(n, amt):
    _withdraw(n, amt, "WITHDRAW", "Cash withdrawal")


def transfer(f, t, amt):
    if f == t:
        raise BankError("Cannot transfer to the same account.")
    _get(t)
    _withdraw(f, amt, "TRANSFER_OUT", f"Transfer to {t}")
    accounts[t]["balance"] += amt; _log(t, "TRANSFER_IN", amt, f"Transfer from {f}")


def close_account(n):
    a = _get(n)
    if a["balance"] > 0:
        raise BankError(f"Withdraw the remaining balance ({a['balance']}) before closing.")
    a["status"] = "CLOSED"
