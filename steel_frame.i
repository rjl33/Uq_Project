[Mesh]
  type = FileMesh
  file = portal_frame2.msh
  dim = 2
[]

[Variables]
  [disp_x] order = FIRST family = LAGRANGE []
  [disp_y] order = FIRST family = LAGRANGE []
  [disp_z] order = FIRST family = LAGRANGE []
  [rot_x]  order = FIRST family = LAGRANGE []
  [rot_y]  order = FIRST family = LAGRANGE []
  [rot_z]  order = FIRST family = LAGRANGE []
[]

[AuxVariables]
  [force_x]  order = CONSTANT family = MONOMIAL []
  [force_y]  order = CONSTANT family = MONOMIAL []
  [force_z]  order = CONSTANT family = MONOMIAL []
  [moment_x] order = CONSTANT family = MONOMIAL []
  [moment_y] order = CONSTANT family = MONOMIAL []
  [moment_z] order = CONSTANT family = MONOMIAL []
[]

[AuxKernels]
  [force_x_aux]
    type = MaterialRealVectorValueAux
    variable = force_x
    property = forces
    component = 0
    block = 'columns roof'
  []
  [force_y_aux]
    type = MaterialRealVectorValueAux
    variable = force_y
    property = forces
    component = 1
    block = 'columns roof'
  []
  [force_z_aux]
    type = MaterialRealVectorValueAux
    variable = force_z
    property = forces
    component = 2
    block = 'columns roof'
  []
  [moment_x_aux]
    type = MaterialRealVectorValueAux
    variable = moment_x
    property = moments
    component = 0
    block = 'columns roof'
  []
  [moment_y_aux]
    type = MaterialRealVectorValueAux
    variable = moment_y
    property = moments
    component = 1
    block = 'columns roof'
  []
  [moment_z_aux]
    type = MaterialRealVectorValueAux
    variable = moment_z
    property = moments
    component = 2
    block = 'columns roof'
  []
[]

[Physics/SolidMechanics/LineElement/QuasiStatic]
  displacements = 'disp_x disp_y disp_z'
  rotations = 'rot_x rot_y rot_z'
  [frame_cols]
    block = columns
    area = 9.5e-3
    y_orientation = '0 0 1'
    Iy = 1.6e-4
    Iz = 2.3e-5
  []
  [roof_beam]
    block = roof
    area = 9.5e-3
    y_orientation = '0 0 1'
    Iy = 1.6e-4
    Iz = 2.3e-5
  []
[]

[Materials]
  [steel]
    type = ComputeElasticityBeam
    youngs_modulus = 2.0e11
    poissons_ratio = 0.3
    shear_coefficient = 0.85
    block = 'columns roof'
  []
  [beam_forces]
    type = ComputeBeamResultants
    block = 'columns roof'
  []
[]

[BCs]
  # Left base: fully fixed
  [fix_left_dx]
    type = DirichletBC
    variable = disp_x
    boundary = left_base
    value = 0.0
  []
  [fix_left_dy]
    type = DirichletBC
    variable = disp_y
    boundary = left_base
    value = 0.0
  []
  [fix_left_dz]
    type = DirichletBC
    variable = disp_z
    boundary = left_base
    value = 0.0
  []
  [fix_left_rx]
    type = DirichletBC
    variable = rot_x
    boundary = left_base
    value = 0.0
  []
  [fix_left_ry]
    type = DirichletBC
    variable = rot_y
    boundary = left_base
    value = 0.0
  []
  [fix_left_rz]
    type = DirichletBC
    variable = rot_z
    boundary = left_base
    value = 0.0
  []
  # Right base: fully fixed
  [fix_right_dx]
    type = DirichletBC
    variable = disp_x
    boundary = right_base
    value = 0.0
  []
  [fix_right_dy]
    type = DirichletBC
    variable = disp_y
    boundary = right_base
    value = 0.0
  []
  [fix_right_dz]
    type = DirichletBC
    variable = disp_z
    boundary = right_base
    value = 0.0
  []
  [fix_right_rx]
    type = DirichletBC
    variable = rot_x
    boundary = right_base
    value = 0.0
  []
  [fix_right_ry]
    type = DirichletBC
    variable = rot_y
    boundary = right_base
    value = 0.0
  []
  [fix_right_rz]
    type = DirichletBC
    variable = rot_z
    boundary = right_base
    value = 0.0
  []
[]

[NodalKernels]
  # Snow: tributary-weighted across 6 roof nodes
  [snow_roof_left_end]
    type = ConstantRate
    variable = disp_y
    boundary = top_left
    rate = -2.0e3
  []
  [snow_roof_1]
    type = ConstantRate
    variable = disp_y
    boundary = roof1
    rate = -4.0e3
  []
  [snow_roof_2]
    type = ConstantRate
    variable = disp_y
    boundary = roof2
    rate = -4.0e3
  []
  [snow_roof_3]
    type = ConstantRate
    variable = disp_y
    boundary = roof3
    rate = -4.0e3
  []
  [snow_roof_4]
    type = ConstantRate
    variable = disp_y
    boundary = roof4
    rate = -4.0e3
  []
  [snow_roof_right_end]
    type = ConstantRate
    variable = disp_y
    boundary = top_right
    rate = -2.0e3
  []
  # Wind: tributary-weighted along left column
  [wind_col_top]
    type = ConstantRate
    variable = disp_x
    boundary = top_left
    rate = 500.0
  []
  [wind_col_4]
    type = ConstantRate
    variable = disp_x
    boundary = col4
    rate = 1000.0
  []
  [wind_col_3]
    type = ConstantRate
    variable = disp_x
    boundary = col3
    rate = 1000.0
  []
  [wind_col_2]
    type = ConstantRate
    variable = disp_x
    boundary = col2
    rate = 1000.0
  []
  [wind_col_1]
    type = ConstantRate
    variable = disp_x
    boundary = col1
    rate = 1000.0
  []
[]

[Postprocessors]
  # Max/min displacements
  [max_disp_x]
    type = NodalExtremeValue
    variable = disp_x
    value_type = max
  []
  [min_disp_x]
    type = NodalExtremeValue
    variable = disp_x
    value_type = min
  []
  [max_disp_y]
    type = NodalExtremeValue
    variable = disp_y
    value_type = max
  []
  [min_disp_y]
    type = NodalExtremeValue
    variable = disp_y
    value_type = min
  []
  # Max forces
  [max_force_x]
    type = ElementExtremeValue
    variable = force_x
    value_type = max
  []
  [max_force_y]
    type = ElementExtremeValue
    variable = force_y
    value_type = max
  []
  # Max/min bending moment (z is the relevant axis for 2D)
  [max_moment_z]
    type = ElementExtremeValue
    variable = moment_z
    value_type = max
  []
  [min_moment_z]
    type = ElementExtremeValue
    variable = moment_z
    value_type = min
  []
[]

[Preconditioning]
  [smp]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  solve_type = PJFNK
  nl_max_its = 20
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-8
  dt = 1
  end_time = 1
[]

[Outputs]
  file_base = portal_frame_out
  exodus = true
  [csv_out]
    type = CSV
    file_base = portal_frame_out
  []
[]