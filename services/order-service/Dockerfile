FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY src ./src
RUN CGO_ENABLED=0 GOOS=linux go build -o order-service ./src/main.go

FROM alpine:3.18
WORKDIR /app
COPY --from=builder /app/order-service .
EXPOSE 3003
CMD ["./order-service"]
