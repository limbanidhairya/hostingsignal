# Makefile for HS-Panel C-Wrappers

CC=gcc
CFLAGS=-O2 -Wall

all: wrap_sysop

wrap_sysop: bin/wrap_sysop.c
	$(CC) $(CFLAGS) -o bin/wrap_sysop bin/wrap_sysop.c

clean:
	rm -f bin/wrap_sysop
