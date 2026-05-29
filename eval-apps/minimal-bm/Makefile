CC = gcc
CFLAGS = -Wall -O2
TARGET = minimal_bm

all: $(TARGET)

$(TARGET): minimal_bm.c
	$(CC) $(CFLAGS) -o $(TARGET) minimal_bm.c

clean:
	rm -f $(TARGET) *.o
