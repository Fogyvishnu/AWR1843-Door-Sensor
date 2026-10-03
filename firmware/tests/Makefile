CC ?= gcc
CFLAGS ?= -Wall -Wextra -Werror -O2 -I../src
LDFLAGS ?= -lm

TARGET = test_door_detector
SRCS = test_door_detector.c ../src/door_detector.c

all: $(TARGET)
	./$(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(TARGET) *.o

.PHONY: all clean
