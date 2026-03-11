# ============================================================================
# Thakran OS — Compositor Build File
# ============================================================================

CC = gcc
CFLAGS = -Wall -Wextra -O3 -std=c11 $(shell pkg-config --cflags wlroots wayland-server xkbcommon)
LDFLAGS = $(shell pkg-config --libs wlroots wayland-server xkbcommon)
SRC = thakran-compositor.c
OUT = thakran-compositor

all: $(OUT)

$(OUT): $(SRC)
	$(CC) $(CFLAGS) -o $(OUT) $(SRC) $(LDFLAGS)

clean:
	rm -f $(OUT)

.PHONY: all clean
