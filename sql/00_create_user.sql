-- OPTIONAL. Run once as an admin user (e.g. SYSTEM) connected to your pluggable DB (XEPDB1 on Oracle XE).
-- Skip this if you already have a schema/user you want to use.
CREATE USER bank IDENTIFIED BY bank123;
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE PROCEDURE, CREATE TRIGGER TO bank;
ALTER USER bank QUOTA UNLIMITED ON USERS;
