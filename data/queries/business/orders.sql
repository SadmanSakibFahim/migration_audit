-- Create Order
INSERT INTO orders (user_id, amount, created_at)
VALUES (:user_id, :amount, CURRENT_TIMESTAMP);

-- Update Order Amount
UPDATE orders
SET amount = :new_amount
WHERE id = :order_id;

-- Delete Order
DELETE FROM orders WHERE id = :order_id;
