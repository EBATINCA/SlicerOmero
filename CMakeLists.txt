cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SlicerOmero)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/SlicerOmero")
set(EXTENSION_CATEGORY "Omero")
set(EXTENSION_CONTRIBUTORS "Idafen Santana (EBATINCA), Borja Fernandez (EBATINCA), Csaba Pinter (EBATINCA), ")
set(EXTENSION_DESCRIPTION "This extension provides functions related to the Omero and Omero.web microscopy platforms.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/SlicerOmero.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/SlicerOmero/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(OmeroConnection)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
