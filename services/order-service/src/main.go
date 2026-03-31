package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "3003"
	}

	r := gin.Default()

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "order-service"})
	})

	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// TODO: add handlers
	// r.POST("/api/orders", handlers.CreateOrder)
	// r.GET("/api/orders/:id", handlers.GetOrder)

	log.Printf("order-service running on :%s", port)
	r.Run(":" + port)
}
