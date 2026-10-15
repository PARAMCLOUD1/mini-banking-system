-- Run once, connected as the bank user:  @install.sql
SET SERVEROUTPUT ON SIZE UNLIMITED
@sql/01_tables.sql
@sql/02_package.sql
@sql/03_sample_data.sql
PROMPT
PROMPT Database ready. Now start the web app:  python app.py
