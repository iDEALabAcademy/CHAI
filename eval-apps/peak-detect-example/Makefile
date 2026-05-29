all: peak-detect

peak-detect: peak_detect.c
	gcc -O0 -g -o main peak_detect.c -lm

clean:
	rm -f main *.o

.PHONY: all clean
