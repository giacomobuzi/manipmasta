# Test host della logica firmware ManipMasta (g++ + mock Arduino)
CXX      ?= g++
CXXFLAGS ?= -std=gnu++17 -O1 -g -Wall -Wextra -Wno-unused-parameter
CPPFLAGS += -DMM_HOST_TEST -Imocks -I../manipmasta

FW_SRC   := $(wildcard ../manipmasta/*.cpp)
MOCK_SRC := mocks/mocks.cpp
TEST_SRC := test_main.cpp
BIN      := build/test_manipmasta

.PHONY: all test clean
all: test

$(BIN): $(FW_SRC) $(MOCK_SRC) $(TEST_SRC) $(wildcard ../manipmasta/*.h) $(wildcard mocks/*.h mocks/avr/*.h)
	@mkdir -p build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(FW_SRC) $(MOCK_SRC) $(TEST_SRC) -o $@

test: $(BIN)
	./$(BIN)

clean:
	rm -rf build
