CC = gcc
CFLAGS = -DLOCAL_RUN

main: sobel.c image_data.h
	$(CC) $(CFLAGS) -include limits.h -o main sobel.c

clean:
	rm -f main