-- 01_tables.sql : tables, sequences, audit trigger
-- Safe to re-run: drops old objects first (errors on first run are harmless)
SET FEEDBACK OFF
BEGIN
  FOR t IN (SELECT object_name n FROM user_objects WHERE object_type = 'TABLE'
            AND object_name IN ('TRANSACTIONS','ACCOUNTS','CUSTOMERS')
            ORDER BY CASE object_name WHEN 'TRANSACTIONS' THEN 1 WHEN 'ACCOUNTS' THEN 2 ELSE 3 END) LOOP
    EXECUTE IMMEDIATE 'DROP TABLE ' || t.n || ' CASCADE CONSTRAINTS';
  END LOOP;
  FOR s IN (SELECT sequence_name n FROM user_sequences
            WHERE sequence_name IN ('SEQ_CUST','SEQ_ACC','SEQ_TXN')) LOOP
    EXECUTE IMMEDIATE 'DROP SEQUENCE ' || s.n;
  END LOOP;
END;
/

CREATE SEQUENCE seq_cust START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE seq_acc  START WITH 1001 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE seq_txn  START WITH 1 INCREMENT BY 1 NOCACHE;

CREATE TABLE customers (
  cust_id    NUMBER        PRIMARY KEY,
  name       VARCHAR2(60)  NOT NULL,
  phone      VARCHAR2(15)  NOT NULL,
  email      VARCHAR2(80),
  created_on DATE          DEFAULT SYSDATE
);

CREATE TABLE accounts (
  acc_no    NUMBER        PRIMARY KEY,
  cust_id   NUMBER        NOT NULL REFERENCES customers(cust_id),
  acc_type  VARCHAR2(10)  NOT NULL CHECK (acc_type IN ('SAVINGS','CURRENT')),
  balance   NUMBER(12,2)  DEFAULT 0 NOT NULL CHECK (balance >= 0),
  status    VARCHAR2(10)  DEFAULT 'ACTIVE' NOT NULL CHECK (status IN ('ACTIVE','CLOSED')),
  opened_on DATE          DEFAULT SYSDATE
);

CREATE TABLE transactions (
  txn_id        NUMBER        PRIMARY KEY,
  acc_no        NUMBER        NOT NULL REFERENCES accounts(acc_no),
  txn_type      VARCHAR2(15)  NOT NULL
                CHECK (txn_type IN ('OPENING','DEPOSIT','WITHDRAW','TRANSFER_OUT','TRANSFER_IN')),
  amount        NUMBER(12,2)  NOT NULL CHECK (amount > 0),
  balance_after NUMBER(12,2)  NOT NULL,
  txn_date      DATE          DEFAULT SYSDATE,
  remarks       VARCHAR2(100)
);

-- Audit rule: transaction history can never be deleted or edited
CREATE OR REPLACE TRIGGER trg_txn_immutable
BEFORE UPDATE OR DELETE ON transactions
BEGIN
  RAISE_APPLICATION_ERROR(-20099, 'Transaction records cannot be changed or deleted.');
END;
/
PROMPT Tables created.
