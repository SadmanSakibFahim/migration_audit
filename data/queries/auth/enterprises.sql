-- Create Enterprise
INSERT INTO enterprises (name, subscriber_id, created_at)
VALUES (:name, :subscriber_id, CURRENT_TIMESTAMP);

-- Update Enterprise Name
UPDATE enterprises
SET name = :new_name
WHERE id = :enterprise_id;

-- Delete Enterprise
DELETE FROM enterprises WHERE id = :enterprise_id;
