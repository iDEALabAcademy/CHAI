CC = gcc
CFLAGS = -DLOCAL_RUN
OBJS = sobel-esp.o

main: $(OBJS)
	$(CC) $(CFLAGS) -o main $(OBJS)

sobel-esp.o: sobel-esp.c image_data.h
	$(CC) $(CFLAGS) -c sobel-esp.c

clean:
	rm -f *.o main