cmake_minimum_required(VERSION 3.21)

project(f4rp_native_bridge LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(f4rp_bridge_runtime STATIC
    src/bridge_runtime.cpp
)

target_include_directories(f4rp_bridge_runtime
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_definitions(f4rp_bridge_runtime
    PRIVATE
        WIN32_LEAN_AND_MEAN
        NOMINMAX
)

target_link_libraries(f4rp_bridge_runtime
    PRIVATE
        winhttp
)

add_executable(f4rp_bridge_smoketest
    src/smoketest_main.cpp
)

target_link_libraries(f4rp_bridge_smoketest
    PRIVATE
        f4rp_bridge_runtime
)
