package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
)

var lockStrategy string

func main() {
	initDB()

	lockStrategy = os.Getenv("LOCK_STRATEGY")
	if lockStrategy == "" {
		lockStrategy = "pessimistic"
	}

	r := mux.NewRouter()
	r.HandleFunc("/orders", PlaceOrder).Methods("POST")
	r.HandleFunc("/health", HealthCheck).Methods("GET")

	log.Printf("order-service listening on :8081 (lock_strategy=%s)", lockStrategy)
	log.Fatal(http.ListenAndServe(":8081", r))
}
