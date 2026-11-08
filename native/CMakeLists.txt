cmake_minimum_required(VERSION 3.16)
project(kingdom_native CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_POSITION_INDEPENDENT_CODE ON)   # GDExtension 공유 라이브러리에 그대로 넣는다

add_library(kingdom_core STATIC core/sim_core.cpp)
target_include_directories(kingdom_core PUBLIC core)
target_compile_options(kingdom_core PRIVATE -Wall -Wextra)

add_executable(sim_bench tools/sim_bench.cpp)
target_link_libraries(sim_bench kingdom_core)
