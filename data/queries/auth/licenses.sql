-- Create License
INSERT INTO licenses (key_hash, plan_tier, valid_from, valid_until, is_active)
VALUES (:key_hash, :plan_tier, :valid_from, :valid_until, :is_active);

-- Update License Validity
UPDATE licenses
SET valid_until = :new_valid_until, is_active = :is_active
WHERE id = :license_id;

-- Deactivate License
UPDATE licenses
SET is_active = 0
WHERE id = :license_id;

-- Delete License (Cascade warning: this will delete subscribers)
DELETE FROM licenses WHERE id = :license_id;
