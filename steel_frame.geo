L = 10.0;
H = 4.0;

// Corner points
Point(1) = {0,   0,  0};
Point(2) = {0,   H,  0};
Point(3) = {L,   H,  0};
Point(4) = {L,   0,  0};

// Left column intermediate points (every 2.0m)
Point(9)  = {0, 0.8, 0};
Point(10) = {0, 1.6, 0};
Point(11) = {0, 2.4, 0};
Point(12) = {0, 3.2, 0};

// Roof intermediate points (every 3.0m)
Point(5) = {2.0,  H, 0};
Point(6) = {4.0,  H, 0};
Point(7) = {6.0,  H, 0};
Point(8) = {8.0, H, 0};

// Left column segments
Line(20) = {1,  9};
Line(21) = {9,  10};
Line(22) = {10, 11};
Line(23) = {11, 12};
Line(24) = {12, 2};

// Right column
Line(2) = {4, 3};

// Roof segments
Line(10) = {2, 5};
Line(11) = {5, 6};
Line(12) = {6, 7};
Line(13) = {7, 8};
Line(14) = {8, 3};

// Mesh seeding
Transfinite Line {20, 21, 22, 23, 24} = 2 Using Progression 1;
Transfinite Line {2} = 6 Using Progression 1;
Transfinite Line {10, 11, 12, 13, 14} = 2 Using Progression 1;

// Physical groups
Physical Curve("columns") = {20, 21, 22, 23, 24, 2};
Physical Curve("roof")    = {10, 11, 12, 13, 14};

Physical Point("left_base")  = {1};
Physical Point("top_left")   = {2};
Physical Point("top_right")  = {3};
Physical Point("right_base") = {4};
Physical Point("roof1")      = {5};
Physical Point("roof2")      = {6};
Physical Point("roof3")      = {7};
Physical Point("roof4")      = {8};
Physical Point("col1")       = {9};
Physical Point("col2")       = {10};
Physical Point("col3")       = {11};
Physical Point("col4")       = {12};