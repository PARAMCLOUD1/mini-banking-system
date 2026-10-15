"""Run from the project folder:  python tests/test_app.py
Tests the Flask routes/templates against an in-memory fake of db.py (no Oracle needed)."""
import os, sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fake_db
sys.modules["db"] = fake_db          # app.py will import the fake instead of the Oracle layer
import app as bank

bank.app.config["TESTING"] = True
c = bank.app.test_client()
passed = 0


def check(name, cond):
    global passed
    assert cond, "FAILED: " + name
    passed += 1
    print("ok  -", name)


def page(url, **kw):
    return c.get(url, follow_redirects=True, **kw).get_data(as_text=True)


def post(url, data):
    return c.post(url, data=data, follow_redirects=True).get_data(as_text=True)


fake_db.reset()
check("empty dashboard renders", "No accounts yet" in page("/"))
check("customers page renders", "Add customer" in page("/customers"))
check("open-account page renders", "Opening deposit" in page("/accounts/new"))

check("bad phone rejected", "phone must be 10 digits" in post("/customers", {"name": "X", "phone": "123"}))
check("customer created", "Customer created with ID 1" in post("/customers", {"name": "Aman", "phone": "9876543210", "email": ""}))
post("/customers", {"name": "Simran", "phone": "9812345678", "email": "s@x.com"})

check("savings below minimum rejected",
      "at least 500" in post("/accounts/new", {"cust_id": "1", "acc_type": "SAVINGS", "initial": "100"}))
check("unknown customer rejected",
      "does not exist" in post("/accounts/new", {"cust_id": "99", "acc_type": "CURRENT", "initial": "0"}))
body = post("/accounts/new", {"cust_id": "1", "acc_type": "SAVINGS", "initial": "5000"})
check("account opened and detail shown", "Account 1001 opened" in body and "5,000.00" in body)
post("/accounts/new", {"cust_id": "2", "acc_type": "CURRENT", "initial": ""})

check("deposit works", "Deposited 250.50" in post("/accounts/1001/deposit", {"amount": "250.50"}))
check("balance updated", "5,250.50" in page("/accounts/1001"))
check("deposit of zero rejected", "positive" in post("/accounts/1001/deposit", {"amount": "0"}))
check("deposit of text rejected", "valid amount" in post("/accounts/1001/deposit", {"amount": "abc"}))
check("3 decimals rejected", "2 decimal" in post("/accounts/1001/deposit", {"amount": "1.234"}))
check("savings minimum balance enforced", "Insufficient funds" in post("/accounts/1001/withdraw", {"amount": "5000"}))
check("withdraw works", "Withdrew 750.00" in post("/accounts/1001/withdraw", {"amount": "750"}))

check("transfer works", "Transferred 1,000.00 to account 1002" in
      post("/accounts/1001/transfer", {"to_acc": "1002", "amount": "1000"}))
check("receiver balance", "1,000.00" in page("/accounts/1002"))
check("transfer to self rejected", "same account" in post("/accounts/1001/transfer", {"to_acc": "1001", "amount": "10"}))
check("transfer to missing account rejected", "does not exist" in post("/accounts/1001/transfer", {"to_acc": "5555", "amount": "10"}))
check("transfer non-numeric account rejected", "must be a number" in post("/accounts/1001/transfer", {"to_acc": "x", "amount": "10"}))

stmt = page("/accounts/1001")
check("statement lists transaction types", all(t in stmt for t in ("OPENING", "DEPOSIT", "WITHDRAW", "TRANSFER_OUT")))
check("dashboard totals", "Total deposits" in page("/") and "1001" in page("/"))
check("customers list shows account count", "Simran" in page("/customers"))

check("close with balance rejected", "before closing" in post("/accounts/1002/close", {}))
post("/accounts/1002/withdraw", {"amount": "1000"})
check("close with zero balance works", "Account closed" in post("/accounts/1002/close", {}))
closed = page("/accounts/1002")
check("closed account hides action forms", "CLOSED" in closed and "Deposit</h2>" not in closed)
check("closed account blocks deposit", "is closed" in post("/accounts/1002/deposit", {"amount": "5"}))
check("missing account is 404", c.get("/accounts/9999").status_code == 404)
check("html is escaped", "&lt;b&gt;" in (post("/customers", {"name": "<b>x</b>", "phone": "9000000000", "email": ""}) and page("/customers")))
print(f"\nAll {passed} checks passed.")
