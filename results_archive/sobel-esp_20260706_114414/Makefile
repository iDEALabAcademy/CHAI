# Makefile content

CC = gcc
CFLAGS = -DLOCAL_RUN

main: sobel-esp.c image_data.h
	$(CC) $(CFLAGS) -o main sobel-esp.c

clean:
	rm -f main