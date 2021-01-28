% Specify an Exasim version to run
version = "Version0.1";

% Add Exasim to Matlab search path
cdir = pwd(); ii = strfind(cdir, "Exasim");
run(cdir(1:(ii+5)) + "/Installation/setpath.m");

% initialize pde structure and mesh structure
[pde,mesh] = initializeexasim(version);

% Define a PDE model: governing equations, initial solutions, and boundary conditions
pde.model = "ModelC";          % ModelC, ModelD, ModelW
pde.modelfile = "pdemodel";    % name of a file defining the PDE model

% Choose computing platform and set number of processors
%pde.platform = "gpu";         % choose this option if NVIDIA GPUs are available
pde.mpiprocs = 4;              % number of MPI processors

% Set discretization parameters, physical parameters, and solver parameters
pde.porder = 2;          % polynomial degree
pde.torder = 2;          % time-stepping order of accuracy
pde.nstage = 2;          % time-stepping number of stages
pde.dt = 0.0001*ones(1000,1);   % time step sizes
pde.saveSolFreq = 100;          % solution is saved every 10 time steps
pde.soltime = 1000; % steps at which solution are collected
pde.visdt = pde.dt(1);           % visualization timestep size
pde.timestepOffset = 0;

gam = 1.4;              % specific heat ratio
Minf = 0.2;             % Mach number
alpha = 2*pi/180;
rinf = 1.0;             % freestream density
uinf = cos(alpha);      % freestream x-horizontal velocity
vinf = 0.0;             % freestream y-horizontal velocity
winf = sin(alpha);      % freestream vertical velocity
pinf = 1/(gam*Minf^2);  % freestream pressure
rEinf = 0.5+pinf/(gam-1); % freestream energy
pde.physicsparam = [gam Re Pr Minf rinf uinf vinf winf rEinf];

pde.tau = 5.0;          % DG stabilization parameter

pde.GMRESrestart=50;  % number of GMRES restarts
pde.linearsolvertol=0.001; % GMRES tolerance
pde.linearsolveriter=1000;  % number of GMRES iterations
pde.precMatrixType=2; % preconditioning type
pde.NLtol = 1e-7;  % Newton tolerance
pde.NLiter = 4;   % number of Newton iterations

% read a grid from a file
load("mesh/P");
load("mesh/T");
load("mesh/dgNodes");
mesh.p = P/6000;
mesh.t = T;
mesh.dgnodes = dgNodes/6000;

im = [1,3,6,10];
for i = 1:size(T,2)
    P(:,T(:,i)) = dgNodes(im,:,i)';
end

% expressions for domain boundaries
mesh.boundaryexpr = {@(p) sqrt(sum(p.^2,1))<9, @(p) sqrt(sum(p.^2,1))>9};
mesh.boundarycondition = [1;2];

% call exasim to generate and run C++ code to solve the PDE model
[sol,pde,mesh] = exasim(pde,mesh);

% visualize the numerical solution of the PDE model using Paraview
%pde.visscalars = {"density", 1, "energy", 5};  % list of scalar fields for visualization
%pde.visvectors = {"momentum", [2, 3, 4]}; % list of vector fields for visualization
%xdg = vis(sol,pde,mesh); % visualize the numerical solution
%disp("Done!");
