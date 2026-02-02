-- Create Subscriber
INSERT INTO subscribers (type, license_key_id, is_active)
VALUES (:type, :license_key_id, 1);

-- Update Subscriber Status
UPDATE subscribers
SET is_active = :is_active
WHERE id = :subscriber_id;

-- Delete Subscriber
DELETE FROM subscribers WHERE id = :subscriber_id;
