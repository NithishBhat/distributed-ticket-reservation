package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq"
)

var db *sql.DB

func initDB() {
	host := os.Getenv("DB_HOST")
	port := os.Getenv("DB_PORT")
	user := os.Getenv("DB_USER")
	password := os.Getenv("DB_PASSWORD")
	dbname := os.Getenv("DB_NAME")

	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=require",
		host, port, user, password, dbname)

	var err error
	db, err = sql.Open("postgres", connStr)
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}

	if err = db.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}

	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)

	log.Println("Connected to PostgreSQL")

	migrateAndSeed()
}

func migrateAndSeed() {
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS tickets (
			id                SERIAL PRIMARY KEY,
			name              VARCHAR(255) NOT NULL,
			quantity          INT NOT NULL CHECK (quantity > 0),
			tickets_reserved  INT NOT NULL DEFAULT 0,
			created_at        TIMESTAMP DEFAULT NOW(),
			CONSTRAINT no_oversell CHECK (tickets_reserved <= quantity)
		);
		CREATE TABLE IF NOT EXISTS orders (
			order_id        SERIAL PRIMARY KEY,
			ticket_id       INT NOT NULL REFERENCES tickets(id),
			idempotency_key VARCHAR(255) NOT NULL UNIQUE,
			quantity        INT NOT NULL CHECK (quantity > 0),
			status          VARCHAR(20) NOT NULL DEFAULT 'confirmed',
			created_at      TIMESTAMP DEFAULT NOW()
		);
		CREATE INDEX IF NOT EXISTS idx_orders_idempotency ON orders(idempotency_key);
		CREATE INDEX IF NOT EXISTS idx_orders_ticket ON orders(ticket_id);
	`)
	if err != nil {
		log.Fatalf("Failed to run migrations: %v", err)
	}

	var count int
	db.QueryRow("SELECT COUNT(*) FROM tickets").Scan(&count)
	if count == 0 {
		_, err = db.Exec(`
			INSERT INTO tickets (name, quantity) VALUES
				('NBA Finals Game 7', 20000),
				('Super Bowl LXII', 70000),
				('World Cup Final', 80000),
				('Concert - Taylor Swift', 50000)
		`)
		if err != nil {
			log.Fatalf("Failed to seed tickets: %v", err)
		}
		log.Println("Seeded 4 tickets")
	}

	log.Println("Migration complete")
}
