CC = gcc
CFLAGS = -DLOCAL_RUN
OBJ = sobel-esp.o

main: $(OBJ)
	$(CC) $(CFLAGS) -o main $(OBJ)

sobel-esp.o: sobel-esp.c image_data.h
	$(CC) $(CFLAGS) -c sobel-esp.c

clean:
	rm -f main $(OBJ)