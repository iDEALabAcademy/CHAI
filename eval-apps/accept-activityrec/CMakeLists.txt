cmake_minimum_required(VERSION 3.0)

FOREACH(METHOD "MS" "AS" "QR")
  set(TESTNAME "accept-activityrec-${METHOD}-${TARGET_ARCH}")
  add_executable( ${TESTNAME}
    main.c
  )

  target_compile_options(${TESTNAME} PRIVATE -Os)
  target_link_libraries(${TESTNAME} PRIVATE m)

  include(${CMAKE_CURRENT_LIST_DIR}/../cmake/tail.cmake)
ENDFOREACH()
