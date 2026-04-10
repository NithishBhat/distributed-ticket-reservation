package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

type Ticket struct {
	ID              int    `json:"id"`
	Name            string `json:"name"`
	Quantity        int    `json:"quantity"`
	TicketsReserved int    `json:"tickets_reserved"`
}

func HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

func GetAllTickets(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	cacheKey := "ticket:all"

	// Try Redis first if caching is enabled.
	if cacheEnabled && rdb != nil {
		cached, err := rdb.Get(ctx, cacheKey).Result()
		if err == nil {
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("X-Cache", "HIT")
			w.Write([]byte(cached))
			return
		}
	}

	// Cache miss (or cache disabled): read from PostgreSQL.
	rows, err := db.Query("SELECT id, name, quantity, tickets_reserved FROM tickets")
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var tickets []Ticket
	for rows.Next() {
		var t Ticket
		if err := rows.Scan(&t.ID, &t.Name, &t.Quantity, &t.TicketsReserved); err != nil {
			http.Error(w, "Scan error", http.StatusInternalServerError)
			return
		}
		tickets = append(tickets, t)
	}

	// Encode once so the same JSON can be returned to the client
	// and stored in Redis.
	respBytes, err := json.Marshal(tickets)
	if err != nil {
		http.Error(w, "Encoding error", http.StatusInternalServerError)
		return
	}

	// Store fresh result in Redis with TTL.
	if cacheEnabled && rdb != nil {
		_ = rdb.Set(ctx, cacheKey, respBytes, cacheTTL).Err()
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Cache", "MISS")
	w.Write(respBytes)
}

func ValidateNoOverselling(w http.ResponseWriter, r *http.Request) {
	rows, err := db.Query("SELECT id, name, quantity, tickets_reserved FROM tickets WHERE tickets_reserved > quantity")
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var violations []Ticket
	for rows.Next() {
		var t Ticket
		if err := rows.Scan(&t.ID, &t.Name, &t.Quantity, &t.TicketsReserved); err != nil {
			http.Error(w, "Scan error", http.StatusInternalServerError)
			return
		}
		violations = append(violations, t)
	}

	w.Header().Set("Content-Type", "application/json")
	if len(violations) == 0 {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"valid":      true,
			"violations": []Ticket{},
		})
	} else {
		w.WriteHeader(http.StatusConflict)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"valid":      false,
			"violations": violations,
		})
	}
}

func GetTicketByID(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	idStr := mux.Vars(r)["id"]
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, "Invalid ticket ID", http.StatusBadRequest)
		return
	}

	cacheKey := fmt.Sprintf("ticket:id:%d", id)

	// Try Redis first if caching is enabled.
	if cacheEnabled && rdb != nil {
		cached, err := rdb.Get(ctx, cacheKey).Result()
		if err == nil {
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("X-Cache", "HIT")
			w.Write([]byte(cached))
			return
		}
	}

	// Cache miss (or cache disabled): read from PostgreSQL.
	var t Ticket
	err = db.QueryRow("SELECT id, name, quantity, tickets_reserved FROM tickets WHERE id = $1", id).
		Scan(&t.ID, &t.Name, &t.Quantity, &t.TicketsReserved)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Ticket not found", http.StatusNotFound)
			return
		}
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	// Encode once so the same JSON can be returned to the client
	// and stored in Redis.
	respBytes, err := json.Marshal(t)
	if err != nil {
		http.Error(w, "Encoding error", http.StatusInternalServerError)
		return
	}

	// Store fresh result in Redis with TTL.
	if cacheEnabled && rdb != nil {
		_ = rdb.Set(ctx, cacheKey, respBytes, cacheTTL).Err()
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Cache", "MISS")
	w.Write(respBytes)
}