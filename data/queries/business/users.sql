-- Create Business User
INSERT INTO users (name, amount, category, status, created_at)
VALUES (:name, :amount, :category, :status, CURRENT_TIMESTAMP);

-- Update User Amount
UPDATE users
SET amount = :new_amount
WHERE id = :user_id;

-- Update User Status
UPDATE users
SET status = :new_status
WHERE id = :user_id;

-- Delete User
DELETE FROM users WHERE id = :user_id;
