-- =====================================================================
-- REFERENCE DDL - documentation of the four core tables (Module 6).
--
-- The supported way to create the schema is:  python manage.py migrate
-- (Django also creates framework tables: django_session, auth_*, token_blacklist_*...)
--
-- Use this file to READ the schema, or to build a scratch copy:
--   CREATE DATABASE ccp_scratch; USE ccp_scratch;  -- then run this script.
-- Do NOT run it in credit_card_payments before 'migrate' (tables would clash).
-- =====================================================================
USE credit_card_payments;

CREATE TABLE IF NOT EXISTS users (
  id            BIGINT       NOT NULL AUTO_INCREMENT,
  password      VARCHAR(128) NOT NULL COMMENT 'PBKDF2-SHA256 hash, never plain text',
  last_login    DATETIME(6)  NULL,
  is_superuser  TINYINT(1)   NOT NULL,
  username      VARCHAR(150) NOT NULL,
  first_name    VARCHAR(150) NOT NULL,
  last_name     VARCHAR(150) NOT NULL,
  email         VARCHAR(254) NOT NULL,
  is_staff      TINYINT(1)   NOT NULL,
  is_active     TINYINT(1)   NOT NULL,
  date_joined   DATETIME(6)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cards (
  id               BIGINT      NOT NULL AUTO_INCREMENT,
  user_id          BIGINT      NOT NULL,
  cardholder_name  VARCHAR(100) NOT NULL,
  brand            VARCHAR(20)  NOT NULL COMMENT 'VISA | MASTERCARD | AMEX | DISCOVER | OTHER',
  card_type        VARCHAR(10)  NOT NULL COMMENT 'CREDIT | DEBIT',
  masked_number    VARCHAR(19)  NOT NULL COMMENT 'e.g. **** **** **** 4242 - the ONLY card number stored',
  last4            VARCHAR(4)   NOT NULL,
  expiry_month     SMALLINT UNSIGNED NOT NULL,
  expiry_year      SMALLINT UNSIGNED NOT NULL,
  created_at       DATETIME(6)  NOT NULL,
  PRIMARY KEY (id),
  KEY idx_cards_user (user_id),
  CONSTRAINT fk_cards_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
  -- NOTE: there is intentionally NO card_number and NO cvv column.
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transactions (
  id             BIGINT        NOT NULL AUTO_INCREMENT,
  reference      VARCHAR(36)   NOT NULL COMMENT 'public UUID',
  user_id        BIGINT        NOT NULL,
  card_id        BIGINT        NULL COMMENT 'NULL after the card is deleted; history is kept',
  card_last4     VARCHAR(4)    NOT NULL COMMENT 'snapshot so history survives card deletion',
  amount         DECIMAL(12,2) NOT NULL,
  currency       VARCHAR(3)    NOT NULL,
  description    VARCHAR(255)  NOT NULL,
  status         VARCHAR(10)   NOT NULL COMMENT 'PENDING -> SUCCESS | FAILED',
  failure_reason VARCHAR(255)  NOT NULL,
  created_at     DATETIME(6)   NOT NULL,
  updated_at     DATETIME(6)   NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_txn_reference (reference),
  KEY idx_txn_user (user_id),
  KEY idx_txn_card (card_id),
  KEY idx_txn_status (status),
  KEY idx_txn_created (created_at),
  CONSTRAINT fk_txn_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT,
  CONSTRAINT fk_txn_card FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admin_logs (
  id          BIGINT       NOT NULL AUTO_INCREMENT,
  admin_id    BIGINT       NULL,
  action      VARCHAR(50)  NOT NULL,
  target_type VARCHAR(50)  NOT NULL,
  target_id   VARCHAR(64)  NOT NULL,
  details     LONGTEXT     NOT NULL,
  ip_address  VARCHAR(39)  NULL,
  created_at  DATETIME(6)  NOT NULL,
  PRIMARY KEY (id),
  KEY idx_admin_logs_action (action),
  KEY idx_admin_logs_admin (admin_id),
  CONSTRAINT fk_admin_logs_admin FOREIGN KEY (admin_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
