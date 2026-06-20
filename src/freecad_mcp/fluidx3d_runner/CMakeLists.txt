cmake_minimum_required(VERSION 3.20)
project(fluidx3d-runner LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find OpenCL
find_package(OpenCL REQUIRED)

# Collect all FluidX3D source files (require FLUIDX3D_SOURCE_DIR)
if(NOT DEFINED FLUIDX3D_SOURCE_DIR)
    message(FATAL_ERROR "FLUIDX3D_SOURCE_DIR must be set to FluidX3D clone path")
endif()

file(GLOB F3D_SOURCES "${FLUIDX3D_SOURCE_DIR}/src/*.cpp")
list(APPEND F3D_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/runner.cpp")

add_executable(fluidx3d-runner ${F3D_SOURCES})
target_include_directories(fluidx3d-runner PRIVATE ${FLUIDX3D_SOURCE_DIR})
target_link_libraries(fluidx3d-runner PRIVATE OpenCL::OpenCL)

# Platform-specific settings
if(WIN32)
    set_target_properties(fluidx3d-runner PROPERTIES
        COMPILE_FLAGS "/EHsc /O2"
    )
else()
    set_target_properties(fluidx3d-runner PROPERTIES
        COMPILE_FLAGS "-O3"
    )
endif()
