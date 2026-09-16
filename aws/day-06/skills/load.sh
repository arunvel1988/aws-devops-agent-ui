#!/bin/bash


BASE_URL="127.0.0.1"

echo "=========================================="
echo " E-Commerce Traffic Generator"
echo "=========================================="
echo "Target: $BASE_URL"
echo "Press CTRL+C to stop"
echo

while true
do

    # --------------------------------------------------------
    # Normal homepage traffic
    # --------------------------------------------------------

    curl -s "$BASE_URL/" > /dev/null

    # --------------------------------------------------------
    # Health checks
    # --------------------------------------------------------

    curl -s "$BASE_URL/health" > /dev/null

    # --------------------------------------------------------
    # Product browsing
    # --------------------------------------------------------

    curl -s "$BASE_URL/products" > /dev/null

    # --------------------------------------------------------
    # Checkout traffic
    # --------------------------------------------------------

    curl -s "$BASE_URL/checkout" > /dev/null

    # --------------------------------------------------------
    # Random 404
    # --------------------------------------------------------

    curl -s "$BASE_URL/product/does-not-exist" > /dev/null

    # --------------------------------------------------------
    # Occasionally generate application errors
    # --------------------------------------------------------

    if [ $((RANDOM % 5)) -eq 0 ]; then
        curl -s "$BASE_URL/error" > /dev/null
    fi

    # --------------------------------------------------------
    # Occasionally simulate payment failure
    # --------------------------------------------------------

    if [ $((RANDOM % 8)) -eq 0 ]; then
        curl -s "$BASE_URL/payment-failure" > /dev/null
    fi

    # --------------------------------------------------------
    # Occasionally simulate database failure
    # --------------------------------------------------------

    if [ $((RANDOM % 10)) -eq 0 ]; then
        curl -s "$BASE_URL/database" > /dev/null
    fi

    # --------------------------------------------------------
    # Wait before next traffic cycle
    # --------------------------------------------------------

    sleep 1

done
