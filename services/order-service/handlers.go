package main

import (
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"time"
)

type OrderRequest struct {
	TicketID       int    `json:"ticket_id"`
	Quantity       int    `json:"quantity"`
	IdempotencyKey string `json:"idempotency_key"`
}

type OrderResponse struct {
	OrderID int    `json:"order_id"`
	Status  string `json:"status"`
}

func HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

func PlaceOrder(w http.ResponseWriter, r *http.Request) {
	var req OrderRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.TicketID <= 0 || req.Quantity <= 0 || req.IdempotencyKey == "" {
		http.Error(w, "ticket_id, quantity, and idempotency_key are required", http.StatusBadRequest)
		return
	}

	// Idempotency check
	var existingID int
	var existingStatus string
	err := db.QueryRow("SELECT order_id, status FROM orders WHERE idempotency_key = $1", req.IdempotencyKey).
		Scan(&existingID, &existingStatus)
	if err == nil {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(OrderResponse{OrderID: existingID, Status: existingStatus})
		return
	}

	var orderID int
	var status string

	switch lockStrategy {
	case "optimistic":
		orderID, status, err = reserveOptimistic(req)
	default:
		orderID, status, err = reservePessimistic(req)
	}

	if err != nil {
		if status == "conflict" {
			http.Error(w, "Sold out — no capacity remaining", http.StatusConflict)
			return
		}
		log.Printf("Order failed: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(OrderResponse{OrderID: orderID, Status: status})
}

// ── Pessimistic: SELECT FOR UPDATE ──────────────────────────────────────

func reservePessimistic(req OrderRequest) (int, string, error) {
	tx, err := db.Begin()
	if err != nil {
		return 0, "", err
	}
	defer tx.Rollback()

	var reserved, capacity int
	err = tx.QueryRow("SELECT tickets_reserved, quantity FROM tickets WHERE id = $1 FOR UPDATE", req.TicketID).
		Scan(&reserved, &capacity)
	if err != nil {
		return 0, "", err
	}

	if reserved+req.Quantity > capacity {
		return 0, "conflict", fmt.Errorf("capacity exceeded")
	}

	_, err = tx.Exec("UPDATE tickets SET tickets_reserved = tickets_reserved + $1 WHERE id = $2",
		req.Quantity, req.TicketID)
	if err != nil {
		return 0, "", err
	}

	var orderID int
	err = tx.QueryRow(
		"INSERT INTO orders (ticket_id, idempotency_key, quantity, status) VALUES ($1, $2, $3, 'confirmed') RETURNING order_id",
		req.TicketID, req.IdempotencyKey, req.Quantity).Scan(&orderID)
	if err != nil {
		return 0, "", err
	}

	if err = tx.Commit(); err != nil {
		return 0, "", err
	}

	return orderID, "confirmed", nil
}

// ── Optimistic: conditional UPDATE with retry ───────────────────────────

func reserveOptimistic(req OrderRequest) (int, string, error) {
    maxRetries := 3

    for attempt := 0; attempt < maxRetries; attempt++ {
        tx, err := db.Begin()
        if err != nil {
            return 0, "", err
        }

        result, err := tx.Exec(
            "UPDATE tickets SET tickets_reserved = tickets_reserved + $1 WHERE id = $2 AND tickets_reserved + $1 <= quantity",
            req.Quantity, req.TicketID)
        if err != nil {
            tx.Rollback()
            return 0, "", err
        }

        rowsAffected, _ := result.RowsAffected()
        if rowsAffected == 0 {
            tx.Rollback()
            if attempt < maxRetries-1 {
                backoff := time.Duration(50*(1<<attempt)) * time.Millisecond
                jitter := time.Duration(rand.Intn(50)) * time.Millisecond
                time.Sleep(backoff + jitter)
                continue
            }
            return 0, "conflict", fmt.Errorf("capacity exceeded after retries")
        }

        var orderID int
        err = tx.QueryRow(
            "INSERT INTO orders (ticket_id, idempotency_key, quantity, status) VALUES ($1, $2, $3, 'confirmed') RETURNING order_id",
            req.TicketID, req.IdempotencyKey, req.Quantity).Scan(&orderID)
        if err != nil {
            tx.Rollback()
            return 0, "", err
        }

        if err = tx.Commit(); err != nil {
            return 0, "", err
        }
        return orderID, "confirmed", nil
    }

    return 0, "conflict", fmt.Errorf("capacity exceeded after retries")
}
