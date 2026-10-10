-- =====================================================================
-- STEP 1 (run in MySQL Workbench as root)
-- Creates the database and an application user.
-- Tables are then created by Django:  python manage.py migrate
-- =====================================================================
CREATE DATABASE IF NOT EXISTS credit_card_payments
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'ccp_user'@'localhost'  IDENTIFIED BY 'Ccp_Pass_2024';
CREATE USER IF NOT EXISTS 'ccp_user'@'127.0.0.1' IDENTIFIED BY 'Ccp_Pass_2024';

GRANT ALL PRIVILEGES ON credit_card_payments.* TO 'ccp_user'@'localhost';
GRANT ALL PRIVILEGES ON credit_card_payments.* TO 'ccp_user'@'127.0.0.1';
FLUSH PRIVILEGES;

SELECT 'credit_card_payments database is ready' AS message;
