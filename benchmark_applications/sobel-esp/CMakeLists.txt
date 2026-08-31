cmake_minimum_required(VERSION 3.10)

FOREACH(METHOD "MS" "AS" "QR")
  set(TESTNAME "sobel-esp-${METHOD}-${TARGET_ARCH}")
  add_executable( ${TESTNAME} 
    sobel-esp.c
  )

  # target_link_libraries(${TESTNAME} PRIVATE m)
  target_compile_options(${TESTNAME} PRIVATE -Os)

  include(${CMAKE_CURRENT_LIST_DIR}/../cmake/tail.cmake)
ENDFOREACH()
