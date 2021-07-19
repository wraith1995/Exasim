clc

% Specify an Exasim version to run
version = "Version0.1";

% Add Exasim to Matlab search path
cdir = pwd(); ii = strfind(cdir, "Exasim");
run(cdir(1:(ii+5)) + "/Installation/setpath.m");

% initialize pde structure and mesh structure
[pde,mesh] = initializeexasim(version);

% Choose computing platform and set number of processors
pde.platform = "gpu";         % choose this option if NVIDIA GPUs are available
pde.mpiprocs = 1;              % number of MPI processors

[pde,mesh] = pdeparams(pde,mesh);

% InitialCondition
UDG = initu(mesh,{0,0,0,0,0,0,0,0,0,0,0,0});
UDG = initConditionSteady(mesh,UDG,pde.physicsparam);
% solTime = 10500;
% UDG = getsolution(['dataout/out_t' num2str(solTime)],dmd,master.npe);
mesh.udg = UDG;
mesh = spongeLayerMesh(mesh,pde,pde.physicsparam(16));


% search compilers and set options
pde = setcompilers(pde);       

% generate input files and store them in datain folder
[pde,mesh,master,dmd] = preprocessing(pde,mesh);

% generate source codes and store them in app folder
gencode(pde);

% compile source codes to build an executable file and store it in app folder
compilerstr = compilecode(pde);

% run executable file to compute solution and store it in dataout folder
runstr = runcode(pde);

% get solution from output files in dataout folder
sol = fetchsolution(pde,master,dmd);

disp("Done!");
