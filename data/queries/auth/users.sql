-- Create User
INSERT INTO users (username, password_hash, role, subscriber_id, is_active, created_at)
VALUES (:username, :password_hash, :role, :subscriber_id, 1, CURRENT_TIMESTAMP);

-- Update User Role
UPDATE users
SET role = :new_role
WHERE id = :user_id;

-- Update User Password
UPDATE users
SET password_hash = :new_password_hash
WHERE id = :user_id;

-- Deactivate User
UPDATE users
SET is_active = 0
WHERE id = :user_id;

-- Delete User
DELETE FROM users WHERE id = :user_id;
