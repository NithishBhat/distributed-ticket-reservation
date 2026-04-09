package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/redis/go-redis/v9"
)

var rdb *redis.Client

func initRedis() {
	host := os.Getenv("REDIS_HOST")
	if host == "" {
		log.Println("REDIS_HOST not set — redis lock strategy unavailable")
		return
	}

	rdb = redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:6379", host),
		PoolSize: 20,
	})

	if err := rdb.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}

	log.Println("Connected to Redis")
}
