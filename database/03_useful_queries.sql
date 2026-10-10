-- Handy queries to run in MySQL Workbench after you have made some payments.
USE credit_card_payments;

-- 1. Proof that no full card number / CVV is stored
SELECT id, user_id, brand, card_type, masked_number, last4, expiry_month, expiry_year FROM cards;
SHOW COLUMNS FROM cards;

-- 2. Passwords are hashes
SELECT id, username, LEFT(password, 30) AS password_hash_prefix FROM users;

-- 3. Daily payment summary (same logic as the admin panel)
SELECT DATE(created_at)                                   AS day,
       COUNT(*)                                           AS total,
       SUM(status = 'SUCCESS')                            AS success,
       SUM(status = 'FAILED')                             AS failed,
       SUM(status = 'PENDING')                            AS pending,
       COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount END), 0) AS success_amount
FROM transactions
GROUP BY DATE(created_at)
ORDER BY day DESC;

-- 4. Filtered history (date + amount + status)
SELECT reference, card_last4, amount, status, created_at
FROM transactions
WHERE created_at >= '2025-01-01' AND created_at < '2030-01-01'
  AND amount BETWEEN 10 AND 500
  AND status = 'SUCCESS'
ORDER BY created_at DESC;

-- 5. Admin audit trail
SELECT l.created_at, u.username AS admin, l.action, l.target_type, l.target_id, l.details
FROM admin_logs l LEFT JOIN users u ON u.id = l.admin_id
ORDER BY l.created_at DESC;
