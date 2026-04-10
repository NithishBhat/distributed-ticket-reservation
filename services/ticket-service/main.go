package main

import (
	"log"
	"net/http"

	"github.com/gorilla/mux"
)

func main() {
	initDB()
	initRedis()

	r := mux.NewRouter()
	r.HandleFunc("/tickets", GetAllTickets).Methods("GET")
	r.HandleFunc("/tickets/{id}", GetTicketByID).Methods("GET")
	r.HandleFunc("/validate", ValidateNoOverselling).Methods("GET")
	r.HandleFunc("/health", HealthCheck).Methods("GET")

	log.Println("ticket-service listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", r))
}
