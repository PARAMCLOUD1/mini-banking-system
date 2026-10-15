-- 03_sample_data.sql : a few customers and accounts to play with
DECLARE
  c1 NUMBER; c2 NUMBER; c3 NUMBER; a NUMBER;
BEGIN
  c1 := bank_pkg.add_customer('Aman Sharma', '9876543210', 'aman@example.com');
  c2 := bank_pkg.add_customer('Simran Kaur', '9812345678', 'simran@example.com');
  c3 := bank_pkg.add_customer('Rohit Verma', '9988776655');
  a := bank_pkg.open_account(c1, 'SAVINGS', 10000);   -- 1001
  a := bank_pkg.open_account(c2, 'SAVINGS', 5000);    -- 1002
  a := bank_pkg.open_account(c3, 'CURRENT', 2000);    -- 1003
  bank_pkg.deposit(1001, 2500);
  bank_pkg.withdraw(1002, 1000);
  bank_pkg.transfer(1001, 1003, 1500);
END;
/
PROMPT Sample data loaded (accounts 1001, 1002, 1003).
