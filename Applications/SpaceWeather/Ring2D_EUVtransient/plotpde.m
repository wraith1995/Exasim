close all

% Specify an Exasim version to run
version = "Version0.1";

% Add Exasim to Matlab search path
cdir = pwd(); ii = strfind(cdir, "Exasim");
run(cdir(1:(ii+5)) + "/Installation/setpath.m");

% initialize pde structure and mesh structure
[pde,mesh] = initializeexasim(version);

% Choose computing platform and set number of processors
% pde.platform = "gpu";         % choose this option if NVIDIA GPUs are available
pde.mpiprocs = 1;              % number of MPI processors

[pde,mesh] = pdeparams(pde,mesh); 
pde.dt = 0.02*ones(8800,1);   % time step sizes
pde.visdt = pde.dt(1);         % visualization timestep size
pde.saveSolFreq = 50;          % solution is saved every 100 time steps
pde.soltime = 50:50:length(pde.dt); % steps at which solution are collected
pde.timestepOffset = 0;

% generate input files and store them in datain folder
[pde,mesh,master,dmd] = preprocessing(pde,mesh);

% get solution from output files in dataout folder
sol = fetchsolution(pde,master,dmd);

% % visualize the numerical solution of the PDE model using Paraview
pde.visscalars = {"density", 1, "temperature", 4};  % list of scalar fields for visualization
pde.visvectors = {"velocity", [2, 3]}; % list of vector fields for visualization
% xdg = visSpongeLayer(sol,pde,mesh); % visualize the numerical solution
xdg = vis(sol,pde,mesh); % visualize the numerical solution
disp("Done!");
