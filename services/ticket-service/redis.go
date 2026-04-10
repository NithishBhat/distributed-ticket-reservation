package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

var rdb *redis.Client
var cacheEnabled bool
var cacheTTL time.Duration

func initRedis() {
	cacheEnabled = os.Getenv("ENABLE_CACHE") == "true"

	// Read TTL from environment, but default to 3 seconds if not provided.
	ttlSeconds := 3
	if raw := os.Getenv("CACHE_TTL_SECONDS"); raw != "" {
		if v, err := strconv.Atoi(raw); err == nil && v > 0 {
			ttlSeconds = v
		}
	}
	cacheTTL = time.Duration(ttlSeconds) * time.Second

	// If cache is disabled, stop here and let the service run DB-only mode.
	if !cacheEnabled {
		log.Println("Cache disabled")
		return
	}

	host := os.Getenv("REDIS_HOST")
	if host == "" {
		log.Println("ENABLE_CACHE=true but REDIS_HOST is empty; disabling cache")
		cacheEnabled = false
		return
	}

	rdb = redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:6379", host),
		PoolSize: 20,
	})

	// If Redis is unavailable, disable cache and fall back to PostgreSQL-only reads.
	if err := rdb.Ping(context.Background()).Err(); err != nil {
		log.Printf("Failed to connect to Redis: %v; disabling cache", err)
		cacheEnabled = false
		rdb = nil
		return
	}

	log.Printf("Connected to Redis (cache TTL = %v)", cacheTTL)
}