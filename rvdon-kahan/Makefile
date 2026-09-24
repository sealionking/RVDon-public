# RVDon Kahan — Top-level Makefile
#
# Usage:
#   make            # build library + example
#   make test       # run self-contained tests
#   make valgrind   # memory leak check
#   make clean

CC      = gcc
CFLAGS  = -std=c99 -O2 -Wall -Wextra -Wpedantic -Iinclude
LDFLAGS = -lm

SRC     = src/rvdon_kahan.c
OBJ     = src/rvdon_kahan.o
EXAMPLE = basic_usage

.PHONY: all test valgrind clean test-fastmath

all: $(OBJ) examples/basic_usage.c
	$(CC) $(CFLAGS) -o $(EXAMPLE) examples/basic_usage.c $(SRC) $(LDFLAGS)

$(OBJ): $(SRC) include/rvdon_kahan.h
	$(CC) $(CFLAGS) -c $(SRC) -o $(OBJ)

test: tests/compare.c tests/golden.py $(SRC)
	cd tests && $(MAKE) test

valgrind: tests/compare.c $(SRC)
	cd tests && $(MAKE) valgrind

test-fastmath:
	@echo "Testing -ffast-math rejection..."
	@if $(CC) $(CFLAGS) -ffast-math -c $(SRC) -o /dev/null 2>&1 | grep -q "fast-math"; then \
		echo "PASS: -ffast-math correctly rejected"; \
	else \
		echo "FAIL: -ffast-math was NOT rejected!"; exit 1; \
	fi

clean:
	rm -f $(OBJ) $(EXAMPLE) tests/c_result_*.csv tests/golden_*.csv tests/compare
