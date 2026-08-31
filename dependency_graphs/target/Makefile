# Makefile

CC = gcc
CFLAGS = -fdump-rtl-expand -DLOCAL_RUN
SRC = $(wildcard *.c)
OBJ = $(SRC:.c=.o)
EXEC = app

all: $(EXEC)

$(EXEC): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(EXEC) *.expand