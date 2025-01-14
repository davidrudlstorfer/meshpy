# -*- coding: utf-8 -*-
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
"""This script is used to test the functionality of MeshPy for creating 4C
input files."""

import os

import numpy as np

from meshpy import (
    Beam3rHerm2Line3,
    BoundaryCondition,
    Function,
    GeometrySet,
    InputFile,
    MaterialReissner,
    Rotation,
    mpy,
)
from meshpy.four_c.beam_potential import BeamPotential
from meshpy.four_c.dbc_monitor import linear_time_transformation
from meshpy.four_c.locsys_condition import LocSysCondition
from meshpy.four_c.solid_shell_thickness_direction import (
    get_visualization_third_parameter_direction_hex8,
    set_solid_shell_thickness_direction,
)
from meshpy.mesh_creation_functions.beam_basic_geometry import (
    create_beam_mesh_helix,
    create_beam_mesh_line,
)
from meshpy.utility import is_node_on_plane


def test_four_c_material_numbering(
    assert_results_equal, get_corresponding_reference_file_path
):
    """Test that materials can be added as strings to an input file (as is done
    when importing dat files) and that the numbering with other added materials
    does not lead to materials with double IDs."""

    input_file = InputFile()
    input_file.add(
        """
        --MATERIALS
        // some comment
        MAT 1 MAT_ViscoElastHyper NUMMAT 4 MATIDS 10 11 12 13 DENS 1.3e-6   // density (kg/mm^3), young (N/mm^2)
        MAT 10 ELAST_CoupNeoHooke YOUNG 0.16 NUE 0.45  // 0.16 (MPa)
        MAT 11 VISCO_GenMax TAU 0.1 BETA 0.4 SOLVE OST
        MAT 12 ELAST_CoupAnisoExpo K1 2.4e-03 K2 0.14 GAMMA 0.0 K1COMP 0 K2COMP 1 ADAPT_ANGLE No INIT 3 STR_TENS_ID 100 FIBER_ID 1
        MAT 13 ELAST_CoupAnisoExpo K1 5.4e-03 K2 1.24 GAMMA 0.0 K1COMP 0 K2COMP 1 ADAPT_ANGLE No INIT 3 STR_TENS_ID 100 FIBER_ID 2
        MAT 100 ELAST_StructuralTensor STRATEGY Standard

        // other comment
        MAT 2 MAT_ElastHyper NUMMAT 3 MATIDS 20 21 22 DENS 1.3e-6                                            // density (kg/mm^3), young (N/mm^2)
        MAT 20 ELAST_CoupNeoHooke YOUNG 1.23 NUE 0.45                                                 // MPa
        MAT 21 ELAST_CoupAnisoExpo K1 0.4e-03 K2 12.0 GAMMA 0.0 K1COMP 0 K2COMP 1 ADAPT_ANGLE No INIT 3 STR_TENS_ID 200 FIBER_ID 1
        MAT 22 ELAST_CoupAnisoExpo K1 50.2e-03 K2 10.0 GAMMA 0.0 K1COMP 0 K2COMP 1 ADAPT_ANGLE No INIT 3 STR_TENS_ID 200 FIBER_ID 2
        MAT 200 ELAST_StructuralTensor STRATEGY Standard
        """
    )
    input_file.add(MaterialReissner(youngs_modulus=1.0, radius=2.0))
    assert_results_equal(get_corresponding_reference_file_path(), input_file)


def test_four_c_simulation_beam_potential_helix(
    assert_results_equal, get_corresponding_reference_file_path
):
    """Test the correct creation of input files for simulations including beam
    to beam potential interactions."""

    input_file = InputFile()
    mat = MaterialReissner(youngs_modulus=1000, radius=0.5, shear_correction=1.0)

    # define function for line charge density
    fun = Function("COMPONENT 0 SYMBOLIC_FUNCTION_OF_SPACE_TIME t")

    # define the beam potential
    beampotential = BeamPotential(
        input_file,
        pot_law_prefactor=[-1.0e-3, 12.45e-8],
        pot_law_exponent=[6.0, 12.0],
        pot_law_line_charge_density=[1.0, 2.0],
        pot_law_line_charge_density_funcs=[fun, "none"],
    )

    # set headers for static case and beam potential
    beampotential.add_header(
        potential_type="Volume",
        cutoff_radius=10.0,
        evaluation_strategy="SingleLengthSpecific_SmallSepApprox_Simple",
        regularization_type="linear_extrapolation",
        regularization_separation=0.1,
        integration_segments=2,
        gauss_points=50,
        potential_reduction_length=15.0,
        automatic_differentiation=False,
        choice_master_slave="lower_eleGID_is_slave",
    )
    beampotential.add_runtime_output(every_iteration=True)

    # create helix
    helix_set = create_beam_mesh_helix(
        input_file,
        Beam3rHerm2Line3,
        mat,
        [0.0, 0.0, 1.0],
        [0.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        helix_angle=np.pi / 4,
        height_helix=10,
        n_el=4,
    )

    # add potential charge conditions to helix
    beampotential.add_potential_charge_condition(geometry_set=helix_set["line"])

    # Add boundary condition to bottom node
    input_file.add(
        BoundaryCondition(
            GeometrySet(
                input_file.get_nodes_by_function(
                    is_node_on_plane,
                    normal=[0, 0, 1],
                    origin_distance=0.0,
                    tol=0.1,
                )
            ),
            "NUMDOF 9 ONOFF 1 1 1 1 1 1 0 0 0",
            bc_type=mpy.bc.dirichlet,
        )
    )

    assert_results_equal(get_corresponding_reference_file_path(), input_file)


def test_four_c_solid_shell_direction_detection(
    assert_results_equal,
    get_corresponding_reference_file_path,
    reference_file_directory,
    tmp_path,
):
    """Test the solid shell direction detection functionality."""

    # Test the plates
    mpy.import_mesh_full = True
    mesh_block = InputFile(
        dat_file=reference_file_directory / "4C_input_solid_shell_thickness_blocks.dat"
    )
    # Add a beam element to check the function also works with beam elements
    mat = MaterialReissner()
    create_beam_mesh_line(
        mesh_block, Beam3rHerm2Line3, mat, [0, 0, 0], [1, 0, 0], n_el=1
    )
    # Set the thickness direction and compare result
    set_solid_shell_thickness_direction(mesh_block.elements, selection_type="thickness")
    assert_results_equal(
        get_corresponding_reference_file_path(additional_identifier="blocks"),
        mesh_block,
    )

    # Test the dome
    mesh_dome_original = InputFile(
        dat_file=reference_file_directory / "4C_input_solid_shell_thickness_dome.dat"
    )

    # Test that the thickness version works
    mesh_dome = mesh_dome_original.copy()
    set_solid_shell_thickness_direction(mesh_dome.elements, selection_type="thickness")
    assert_results_equal(
        get_corresponding_reference_file_path(additional_identifier="dome_thickness"),
        mesh_dome,
    )

    # Test that the direction function version works
    def director_function(cell_center):
        """Return director that will be used to determine the solid thickness
        direction."""
        return cell_center / np.linalg.norm(cell_center)

    mesh_dome = mesh_dome_original.copy()
    set_solid_shell_thickness_direction(
        mesh_dome.elements,
        selection_type="projection_director_function",
        director_function=director_function,
    )
    assert_results_equal(
        get_corresponding_reference_file_path(additional_identifier="dome_thickness"),
        mesh_dome,
    )

    # Test that the constant direction version works
    mesh_dome = mesh_dome_original.copy()
    set_solid_shell_thickness_direction(
        mesh_dome.elements,
        selection_type="projection_director",
        director=[0, 0, 1],
        identify_threshold=None,
    )
    assert_results_equal(
        get_corresponding_reference_file_path(
            additional_identifier="dome_constant_direction"
        ),
        mesh_dome,
    )

    # Also test the visualization function
    ref_file = (
        reference_file_directory
        / "test_four_c_solid_shell_direction_detection_dome_constant_direction.vtu"
    )
    test_file = (
        tmp_path
        / "test_four_c_solid_shell_direction_detection_dome_constant_direction_result.vtu"
    )

    grid = get_visualization_third_parameter_direction_hex8(mesh_dome)
    grid.save(test_file)
    assert_results_equal(ref_file, test_file)


def test_meshpy_locsys_condition(
    assert_results_equal, get_corresponding_reference_file_path
):
    """Test case for point locsys condition for beams.

    The testcase is similar to beam3r_herm2line3_static_locsys.dat, but
    with simpler material.
    """

    # Create the input file with function and material.
    input_file = InputFile()

    fun = Function("SYMBOLIC_FUNCTION_OF_SPACE_TIME t")
    input_file.add(fun)

    mat = MaterialReissner()
    input_file.add(mat)

    # Create the beam.
    beam_set = create_beam_mesh_line(
        input_file, Beam3rHerm2Line3, mat, [2.5, 2.5, 2.5], [4.5, 2.5, 2.5], n_el=1
    )

    # Add dirichlet boundary conditions.
    input_file.add(
        BoundaryCondition(
            beam_set["start"],
            "NUMDOF 9 ONOFF 1 1 1 1 1 1 0 0 0 VAL 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 FUNCT 0 0 0 0 0 0 0 0 0",
            bc_type=mpy.bc.dirichlet,
        )
    )
    # Add additional dirichlet boundary condition to check if combination with locsys condition works.
    input_file.add(
        BoundaryCondition(
            beam_set["end"],
            "NUMDOF 9 ONOFF 1 0 0 0 0 0 0 0 0 VAL 1.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 FUNCT 1 0 0 0 0 0 0 0 0",
            bc_type=mpy.bc.dirichlet,
        )
    )

    # Add locsys condition with rotation
    input_file.add(LocSysCondition(beam_set["end"], Rotation([0, 0, 1], 0.1)))

    # Compare with the reference solution.
    assert_results_equal(get_corresponding_reference_file_path(), input_file)


def test_linear_time_transformation_scaling():
    """Test the scaling of the interval for the function.

    Starts with a function within the interval [0,1] and transforms
    them.
    """

    # starting time array
    time = np.array([0, 0.5, 0.75, 1.0])

    # corresponding values 3 values per time step
    force = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])

    # with the result vector
    force_result = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])

    # base case no scaling only
    time_trans, force_trans = linear_time_transformation(
        time, force, [0, 1], flip=False
    )

    # first result is simply the attached
    time_result = np.array([0, 0.5, 0.75, 1.0])

    # check solution
    assert time_trans.tolist() == time_result.tolist()
    assert force_trans.tolist() == force_result.tolist()

    # transform to interval [0, 2]
    time_trans, force_trans = linear_time_transformation(
        time, force, [0, 2], flip=False
    )

    # time values should double
    assert time_trans.tolist() == (2 * time_result).tolist()
    assert force_trans.tolist() == force_result.tolist()

    # new result
    force_result = np.array(
        [[1, 2, 3], [1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [10, 11, 12]]
    )

    # shift to the interval [1 ,2] and add valid start end point
    time_trans, force_trans = linear_time_transformation(
        time, force, [1, 2, 5], flip=False, valid_start_and_end_point=True
    )
    assert time_trans.tolist() == np.array([0, 1.0, 1.5, 1.75, 2.0, 5.0]).tolist()
    assert force_trans.tolist() == force_result.tolist()


def test_linear_time_transformation_flip():
    """Test the flip flag option of linear_time_transformation to mirror the
    function."""

    # base case no scaling no end points should be attached
    # starting time array
    time = np.array([0, 0.5, 0.75, 1.0])

    # corresponding values:  3 values per time step
    force = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])

    # first result is simply the attached point at the end
    time_result = np.array([0, 0.25, 0.5, 1.0])

    # with the value vector:
    force_result = np.array([[10, 11, 12], [7, 8, 9], [4, 5, 6], [1, 2, 3]])

    # base case no scaling only end points should be attached
    time_trans, force_trans = linear_time_transformation(time, force, [0, 1], flip=True)

    # check solution
    assert time_result.tolist() == time_trans.tolist()
    assert force_trans.tolist() == force_result.tolist()

    # new force result
    force_result = np.array([[10, 11, 12], [7, 8, 9], [4, 5, 6], [1, 2, 3]])

    time_result = np.array([0, 0.25, 0.5, 1.0]) + 1

    # test now an shift to the interval [1 ,2]
    time_trans, force_trans = linear_time_transformation(time, force, [1, 2], flip=True)
    assert time_result.tolist() == time_trans.tolist()
    assert force_trans.tolist() == force_result.tolist()

    # same trick as above but with 2
    time_result = np.array([0, 2.0, 2.25, 2.5, 3.0, 5.0])
    # new force result
    force_result = np.array(
        [[10, 11, 12], [10, 11, 12], [7, 8, 9], [4, 5, 6], [1, 2, 3], [1, 2, 3]]
    )

    # test offset and scaling and add valid start and end point
    time_trans, force_trans = linear_time_transformation(
        time, force, [2, 3, 5], flip=True, valid_start_and_end_point=True
    )
    assert time_result.tolist() == time_trans.tolist()
    assert force_trans.tolist() == force_result.tolist()