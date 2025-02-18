# MeshPy: A beam finite element input generator
#
# MIT License
#
# Copyright (c) 2018-2025
#     Ivo Steinbrecher
#     Institute for Mathematics and Computer-Based Simulation
#     Universitaet der Bundeswehr Muenchen
#     https://www.unibw.de/imcs-en
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Compile the Cython code."""

import importlib.util
from distutils.command.build_ext import build_ext
from distutils.core import Distribution
from distutils.extension import Extension

import numpy as np


def compile_cython():
    """Compile the Cython code.

    Only compile the code if Cython is installed.
    """

    # Check if Cython is installed
    if importlib.util.find_spec("Cython") is None:
        return
    else:
        from Cython.Build import cythonize

    # Define the Cython extension
    extensions = [
        Extension(
            "meshpy.geometric_search.geometric_search_cython_lib",
            ["src/meshpy/geometric_search/geometric_search_cython_lib.pyx"],
            include_dirs=[np.get_include()],
        )
    ]

    # Cythonize the extension
    cythonized_extensions = cythonize(
        extensions, build_dir="src/build/cython_generated_code", annotate=True
    )

    # Create a Distribution object with the cythonized extensions
    dist = Distribution({"ext_modules": cythonized_extensions})

    # Set up and run the build_ext command from distutils
    cmd = build_ext(dist)
    cmd.ensure_finalized()
    cmd.run()


if __name__ == "__main__":
    compile_cython()
