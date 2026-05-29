CC = gcc
CFLAGS = -DLOCAL_RUN -lm

all: main

main: main.c
	$(CC) -o main main.c $(CFLAGS)

clean:
	rm -f main output.csv
