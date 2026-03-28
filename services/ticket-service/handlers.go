package main

import (
	"encoding/json"
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

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(tickets)
}

func GetTicketByID(w http.ResponseWriter, r *http.Request) {
	idStr := mux.Vars(r)["id"]
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, "Invalid ticket ID", http.StatusBadRequest)
		return
	}

	var t Ticket
	err = db.QueryRow("SELECT id, name, quantity, tickets_reserved FROM tickets WHERE id = $1", id).
		Scan(&t.ID, &t.Name, &t.Quantity, &t.TicketsReserved)
	if err != nil {
		http.Error(w, "Ticket not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(t)
}
