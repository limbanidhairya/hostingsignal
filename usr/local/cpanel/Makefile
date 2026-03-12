# HostingSignal C-Extensions Makefile
# Used for compiling internal setuid wrappers where necessary

CC=gcc
CFLAGS=-Wall -O2

# Default target
all: wrap_edquota

# C wrappers for high-privilege operations, mimicking cPanel's internal security structure
wrap_edquota: src/wrap_edquota.c
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/wrap_edquota src/wrap_edquota.c
	# In production, this would be setuid root
	# chown root:root bin/wrap_edquota
	# chmod 4755 bin/wrap_edquota

clean:
	rm -rf bin/
