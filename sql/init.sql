CREATE TABLE tickets (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(255) NOT NULL,
    quantity          INT NOT NULL CHECK (quantity > 0),
    tickets_reserved  INT NOT NULL DEFAULT 0,
    created_at        TIMESTAMP DEFAULT NOW(),
    CONSTRAINT no_oversell CHECK (tickets_reserved <= quantity)
);

CREATE TABLE orders (
    order_id        SERIAL PRIMARY KEY,
    ticket_id       INT NOT NULL REFERENCES tickets(id),
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    quantity        INT NOT NULL CHECK (quantity > 0),
    status          VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_idempotency ON orders(idempotency_key);
CREATE INDEX idx_orders_ticket ON orders(ticket_id);

-- Seed test tickets
INSERT INTO tickets (name, quantity) VALUES
    ('NBA Finals Game 7', 20000),
    ('Super Bowl LXII', 70000),
    ('World Cup Final', 80000),
    ('Concert - Taylor Swift', 50000);
