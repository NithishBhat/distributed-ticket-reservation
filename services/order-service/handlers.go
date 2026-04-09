package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/lib/pq"
	"github.com/redis/go-redis/v9"
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
	case "redis":
		orderID, status, err = reserveRedis(req)
	default:
		orderID, status, err = reservePessimistic(req)
	}

	if err != nil {
		var pqErr *pq.Error
		if errors.As(err, &pqErr) {
			// Idempotency race: concurrent request with same key inserted first
			if pqErr.Code == "23505" {
				var eid int
				var es string
				if db.QueryRow("SELECT order_id, status FROM orders WHERE idempotency_key = $1",
					req.IdempotencyKey).Scan(&eid, &es) == nil {
					w.Header().Set("Content-Type", "application/json")
					json.NewEncoder(w).Encode(OrderResponse{OrderID: eid, Status: es})
					return
				}
			}
			// CHECK constraint violation — overselling safety net
			if pqErr.Code == "23514" {
				http.Error(w, "Sold out — no capacity remaining", http.StatusConflict)
				return
			}
		}
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

// ── Redis distributed lock ────────────────────────────────────────────

func reserveRedis(req OrderRequest) (int, string, error) {
	ctx := context.Background()
	// Use a Redis key as a distributed lock for the ticket ID
	lockKey := fmt.Sprintf("lock:ticket:%d", req.TicketID)
	// Unique value to identify our lock ownership, and TTL to prevent deadlocks
	lockVal := uuid.New().String()
	// If the holder crashes or hangs, the lock auto-expires so others aren't blocked forever. It    
	// should be longer than the DB transaction takes (~10-50ms), but short enough to recover quickly from failures.                           
	lockTTL := 3 * time.Second
	maxRetries := 10

	// 1. Acquire lock with retry
	acquired := false
	for attempt := 0; attempt < maxRetries; attempt++ {
		ok, err := rdb.SetNX(ctx, lockKey, lockVal, lockTTL).Result()
		if err != nil {
			return 0, "", fmt.Errorf("redis error: %w", err)
		}
		if ok {
			acquired = true
			break
		}
		// Lock held by someone else — short spin with jitter
		time.Sleep(time.Duration(10+rand.Intn(20)) * time.Millisecond)
	}
	if !acquired {
		return 0, "conflict", fmt.Errorf("could not acquire redis lock")
	}

	// 2. Ensure lock is released when done
	defer func() {
		// Only delete if we still own the lock
		script := redis.NewScript(`
			if redis.call("get", KEYS[1]) == ARGV[1] then
				return redis.call("del", KEYS[1])
			else
				return 0
			end
		`)
		script.Run(ctx, rdb, []string{lockKey}, lockVal)
	}()

	// 3. Do the DB work (no row lock needed — we hold the distributed lock)
	var reserved, capacity int
	err := db.QueryRow("SELECT tickets_reserved, quantity FROM tickets WHERE id = $1", req.TicketID).
		Scan(&reserved, &capacity)
	if err != nil {
		return 0, "", err
	}

	if reserved+req.Quantity > capacity {
		return 0, "conflict", fmt.Errorf("capacity exceeded")
	}

	tx, err := db.Begin()
	if err != nil {
		return 0, "", err
	}
	defer tx.Rollback()

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
