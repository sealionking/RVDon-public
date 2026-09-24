# RVDon Kahan — Test Makefile
#
# Usage:
#   make test       # run all tests
#   make valgrind   # memory leak check
#   make test-fastmath  # verify -ffast-math is rejected

CC      = gcc
CFLAGS  = -std=c99 -O2 -Wall -Wextra -Wpedantic -I../include
LDFLAGS = -lm

SRC     = ../src/rvdon_kahan.c
TEST    = compare.c

.PHONY: all test vectors golden valgrind clean test-fastmath

all: compare

vectors:
	cd vectors && python3 gen_vectors.py

golden: vectors
	python3 golden.py

compare: $(SRC) $(TEST)
	$(CC) $(CFLAGS) $(SRC) $(TEST) -o compare $(LDFLAGS)

test: compare golden
	./compare vectors .

valgrind: compare
	valgrind --leak-check=full --show-leak-kinds=all --error-exitcode=1 \
		./compare vectors .

test-fastmath:
	@echo "Testing -ffast-math rejection..."
	@if $(CC) $(CFLAGS) -ffast-math -c $(SRC) -o /dev/null 2>&1 | grep -q "fast-math"; then \
		echo "PASS: -ffast-math correctly rejected"; \
	else \
		echo "FAIL: -ffast-math was NOT rejected!"; exit 1; \
	fi

clean:
	rm -f compare c_result_*.csv golden_*.csv
