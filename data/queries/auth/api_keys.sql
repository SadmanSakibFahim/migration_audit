-- Create API Key
INSERT INTO api_keys (user_id, key_hash, prefix, created_at, expires_at)
VALUES (:user_id, :key_hash, :prefix, CURRENT_TIMESTAMP, :expires_at);

-- Revoke/Delete API Key
DELETE FROM api_keys WHERE id = :api_key_id;

-- Revoke All Keys for User
DELETE FROM api_keys WHERE user_id = :user_id;
