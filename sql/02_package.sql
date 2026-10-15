-- 02_package.sql : all banking logic lives in one package
CREATE OR REPLACE PACKAGE bank_pkg AS
  c_min_balance CONSTANT NUMBER := 500;   -- minimum balance for SAVINGS accounts

  FUNCTION  add_customer (p_name VARCHAR2, p_phone VARCHAR2, p_email VARCHAR2 DEFAULT NULL) RETURN NUMBER;
  FUNCTION  open_account (p_cust_id NUMBER, p_type VARCHAR2, p_initial NUMBER DEFAULT 0)   RETURN NUMBER;
  PROCEDURE deposit      (p_acc NUMBER, p_amt NUMBER);
  PROCEDURE withdraw     (p_acc NUMBER, p_amt NUMBER);
  PROCEDURE transfer     (p_from NUMBER, p_to NUMBER, p_amt NUMBER);
  FUNCTION  get_balance  (p_acc NUMBER) RETURN NUMBER;
  PROCEDURE mini_statement(p_acc NUMBER, p_rows NUMBER DEFAULT 5);
  PROCEDURE close_account(p_acc NUMBER);
END bank_pkg;
/

CREATE OR REPLACE PACKAGE BODY bank_pkg AS

  -- ---------- private helpers ----------
  PROCEDURE lock_account(p_acc NUMBER, p_bal OUT NUMBER, p_type OUT VARCHAR2) IS
    v_status accounts.status%TYPE;
  BEGIN
    SELECT balance, acc_type, status INTO p_bal, p_type, v_status
    FROM accounts WHERE acc_no = p_acc FOR UPDATE;
    IF v_status <> 'ACTIVE' THEN
      RAISE_APPLICATION_ERROR(-20002, 'Account ' || p_acc || ' is closed.');
    END IF;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      RAISE_APPLICATION_ERROR(-20001, 'Account ' || p_acc || ' does not exist.');
  END lock_account;

  PROCEDURE check_amount(p_amt NUMBER) IS
  BEGIN
    IF p_amt IS NULL OR p_amt <= 0 THEN
      RAISE_APPLICATION_ERROR(-20003, 'Amount must be greater than zero.');
    END IF;
  END check_amount;

  PROCEDURE log_txn(p_acc NUMBER, p_type VARCHAR2, p_amt NUMBER, p_bal NUMBER, p_rem VARCHAR2) IS
  BEGIN
    INSERT INTO transactions (txn_id, acc_no, txn_type, amount, balance_after, remarks)
    VALUES (seq_txn.NEXTVAL, p_acc, p_type, p_amt, p_bal, p_rem);
  END log_txn;

  -- core operations (no COMMIT, so transfer can combine them atomically)
  PROCEDURE do_deposit(p_acc NUMBER, p_amt NUMBER, p_type VARCHAR2, p_rem VARCHAR2) IS
    v_bal NUMBER; v_type VARCHAR2(10);
  BEGIN
    check_amount(p_amt);
    lock_account(p_acc, v_bal, v_type);
    v_bal := v_bal + p_amt;
    UPDATE accounts SET balance = v_bal WHERE acc_no = p_acc;
    log_txn(p_acc, p_type, p_amt, v_bal, p_rem);
  END do_deposit;

  PROCEDURE do_withdraw(p_acc NUMBER, p_amt NUMBER, p_type VARCHAR2, p_rem VARCHAR2) IS
    v_bal NUMBER; v_type VARCHAR2(10); v_floor NUMBER;
  BEGIN
    check_amount(p_amt);
    lock_account(p_acc, v_bal, v_type);
    v_floor := CASE v_type WHEN 'SAVINGS' THEN c_min_balance ELSE 0 END;
    IF v_bal - p_amt < v_floor THEN
      RAISE_APPLICATION_ERROR(-20004, 'Insufficient funds. Balance: ' || v_bal ||
                              ', minimum to maintain: ' || v_floor);
    END IF;
    v_bal := v_bal - p_amt;
    UPDATE accounts SET balance = v_bal WHERE acc_no = p_acc;
    log_txn(p_acc, p_type, p_amt, v_bal, p_rem);
  END do_withdraw;

  -- ---------- public API ----------
  FUNCTION add_customer(p_name VARCHAR2, p_phone VARCHAR2, p_email VARCHAR2 DEFAULT NULL) RETURN NUMBER IS
    v_id NUMBER;
  BEGIN
    IF TRIM(p_name) IS NULL OR NOT REGEXP_LIKE(p_phone, '^[0-9]{10}$') THEN
      RAISE_APPLICATION_ERROR(-20005, 'Name is required and phone must be 10 digits.');
    END IF;
    v_id := seq_cust.NEXTVAL;
    INSERT INTO customers (cust_id, name, phone, email) VALUES (v_id, TRIM(p_name), p_phone, p_email);
    COMMIT;
    RETURN v_id;
  END add_customer;

  FUNCTION open_account(p_cust_id NUMBER, p_type VARCHAR2, p_initial NUMBER DEFAULT 0) RETURN NUMBER IS
    v_acc NUMBER; v_cnt NUMBER; v_type VARCHAR2(10) := UPPER(TRIM(p_type));
  BEGIN
    SELECT COUNT(*) INTO v_cnt FROM customers WHERE cust_id = p_cust_id;
    IF v_cnt = 0 THEN
      RAISE_APPLICATION_ERROR(-20006, 'Customer ' || p_cust_id || ' does not exist.');
    END IF;
    IF v_type NOT IN ('SAVINGS','CURRENT') THEN
      RAISE_APPLICATION_ERROR(-20007, 'Account type must be SAVINGS or CURRENT.');
    END IF;
    IF v_type = 'SAVINGS' AND NVL(p_initial,0) < c_min_balance THEN
      RAISE_APPLICATION_ERROR(-20008, 'SAVINGS needs an opening deposit of at least ' || c_min_balance);
    END IF;
    v_acc := seq_acc.NEXTVAL;
    INSERT INTO accounts (acc_no, cust_id, acc_type, balance) VALUES (v_acc, p_cust_id, v_type, 0);
    IF NVL(p_initial,0) > 0 THEN
      do_deposit(v_acc, p_initial, 'OPENING', 'Opening deposit');
    END IF;
    COMMIT;
    RETURN v_acc;
  END open_account;

  PROCEDURE deposit(p_acc NUMBER, p_amt NUMBER) IS
  BEGIN
    do_deposit(p_acc, p_amt, 'DEPOSIT', 'Cash deposit');
    COMMIT;
  EXCEPTION WHEN OTHERS THEN ROLLBACK; RAISE;
  END deposit;

  PROCEDURE withdraw(p_acc NUMBER, p_amt NUMBER) IS
  BEGIN
    do_withdraw(p_acc, p_amt, 'WITHDRAW', 'Cash withdrawal');
    COMMIT;
  EXCEPTION WHEN OTHERS THEN ROLLBACK; RAISE;
  END withdraw;

  PROCEDURE transfer(p_from NUMBER, p_to NUMBER, p_amt NUMBER) IS
  BEGIN
    IF p_from = p_to THEN
      RAISE_APPLICATION_ERROR(-20009, 'Cannot transfer to the same account.');
    END IF;
    do_withdraw(p_from, p_amt, 'TRANSFER_OUT', 'Transfer to ' || p_to);
    do_deposit (p_to,   p_amt, 'TRANSFER_IN',  'Transfer from ' || p_from);
    COMMIT;   -- both legs succeed together, or neither does
  EXCEPTION WHEN OTHERS THEN ROLLBACK; RAISE;
  END transfer;

  FUNCTION get_balance(p_acc NUMBER) RETURN NUMBER IS
    v_bal NUMBER;
  BEGIN
    SELECT balance INTO v_bal FROM accounts WHERE acc_no = p_acc;
    RETURN v_bal;
  EXCEPTION WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20001, 'Account ' || p_acc || ' does not exist.');
  END get_balance;

  PROCEDURE mini_statement(p_acc NUMBER, p_rows NUMBER DEFAULT 5) IS
    v_bal NUMBER := get_balance(p_acc);   -- also validates the account
  BEGIN
    DBMS_OUTPUT.PUT_LINE('--- Mini statement for account ' || p_acc || ' ---');
    DBMS_OUTPUT.PUT_LINE(RPAD('Date',12) || RPAD('Type',14) || LPAD('Amount',12) || LPAD('Balance',12));
    FOR r IN (SELECT * FROM (SELECT txn_date, txn_type, amount, balance_after
                             FROM transactions WHERE acc_no = p_acc
                             ORDER BY txn_id DESC)
              WHERE ROWNUM <= p_rows) LOOP
      DBMS_OUTPUT.PUT_LINE(RPAD(TO_CHAR(r.txn_date,'DD-MON-YY'),12) || RPAD(r.txn_type,14) ||
                           LPAD(TO_CHAR(r.amount,'FM999,999,990.00'),12) ||
                           LPAD(TO_CHAR(r.balance_after,'FM999,999,990.00'),12));
    END LOOP;
    DBMS_OUTPUT.PUT_LINE('Current balance: ' || TO_CHAR(v_bal,'FM999,999,990.00'));
  END mini_statement;

  PROCEDURE close_account(p_acc NUMBER) IS
    v_bal NUMBER; v_type VARCHAR2(10);
  BEGIN
    lock_account(p_acc, v_bal, v_type);
    IF v_bal > 0 THEN
      RAISE_APPLICATION_ERROR(-20010, 'Withdraw the remaining balance (' || v_bal || ') before closing.');
    END IF;
    UPDATE accounts SET status = 'CLOSED' WHERE acc_no = p_acc;
    COMMIT;
  EXCEPTION WHEN OTHERS THEN ROLLBACK; RAISE;
  END close_account;

END bank_pkg;
/
SHOW ERRORS
PROMPT Package created.
