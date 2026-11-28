cmake_minimum_required(VERSION 3.20)
project(tradegen_fast LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(tradegen_fast SHARED
    src/hp1_continuous.cpp
    src/hp2_hp4_orders_books.cpp
    src/hp3_strategy_carry.cpp
    src/hp5_kis.cpp
    src/hp6_odds_mc.cpp
)

target_include_directories(tradegen_fast PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(tradegen_fast PRIVATE
    -O3
    -fno-fast-math
    -ffp-contract=off
    -fPIC
    -Wall
    -Wextra
)
