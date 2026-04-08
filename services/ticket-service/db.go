package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

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

	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

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
	if count < 50 {
		// Clear old data so IDs start fresh at 1..50
		db.Exec("DELETE FROM orders")
		db.Exec("DELETE FROM tickets")
		db.Exec("ALTER SEQUENCE tickets_id_seq RESTART WITH 1")
		_, err = db.Exec(`
			INSERT INTO tickets (name, quantity) VALUES
				('NBA Finals Game 7', 20000),
				('Super Bowl LXII', 70000),
				('World Cup Final', 80000),
				('Concert - Taylor Swift', 50000),
				('Champions League Final', 60000),
				('Olympics Opening Ceremony', 80000),
				('Grand Prix Monaco', 30000),
				('Wimbledon Final', 15000),
				('Concert - Drake', 45000),
				('Concert - Bad Bunny', 55000),
				('UFC 300', 20000),
				('World Series Game 7', 40000),
				('Rugby World Cup Final', 35000),
				('Cricket World Cup Final', 50000),
				('Concert - Beyonce', 60000),
				('Concert - Ed Sheeran', 50000),
				('NBA All-Star Game', 25000),
				('FIFA Club World Cup', 45000),
				('Concert - Coldplay', 55000),
				('Concert - The Weeknd', 40000),
				('Stanley Cup Finals', 20000),
				('MLS Cup Final', 25000),
				('Concert - Adele', 35000),
				('Concert - Bruno Mars', 30000),
				('Australian Open Final', 15000),
				('US Open Final', 24000),
				('French Open Final', 15000),
				('Tour de France Final', 10000),
				('Concert - Billie Eilish', 40000),
				('Concert - Post Malone', 35000),
				('Concert - Dua Lipa', 45000),
				('Concert - SZA', 40000),
				('Concert - Travis Scott', 50000),
				('Concert - Kendrick Lamar', 45000),
				('Super Bowl Halftime Show', 70000),
				('Daytona 500', 100000),
				('Kentucky Derby', 150000),
				('March Madness Final', 70000),
				('Concert - Rihanna', 55000),
				('Concert - Harry Styles', 40000),
				('Concert - Doja Cat', 35000),
				('Concert - Olivia Rodrigo', 30000),
				('Concert - Morgan Wallen', 45000),
				('Concert - Luke Combs', 35000),
				('Concert - Metallica', 60000),
				('Concert - Foo Fighters', 50000),
				('Boxing Championship', 20000),
				('PGA Championship', 40000),
				('Concert - Sabrina Carpenter', 25000),
				('Concert - Imagine Dragons', 45000)
		`)
		if err != nil {
			log.Fatalf("Failed to seed tickets: %v", err)
		}
		log.Println("Seeded 50 tickets")
	}

	log.Println("Migration complete")
}
