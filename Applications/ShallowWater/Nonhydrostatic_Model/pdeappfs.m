% Specify an Exasim version to run
version = "Version0.3";

% Add Exasim to Matlab search path
cdir = pwd(); ii = strfind(cdir, "Exasim");
run(cdir(1:(ii+5)) + "/Installation/setpath.m");

% initialize pde structure and mesh structure
[pde,mesh] = initializeexasim(version);

% Define a PDE model: governing equations, initial solutions, and boundary conditions
pde.model = "ModelD";          % ModelC, ModelD, ModelW 
pde.modelfile = "pdemodelfs";    % name of a file defining the PDE model

% Choose computing platform and set number of processors
%pde.platform = "gpu";         % choose this option if NVIDIA GPUs are available
pde.mpiprocs = 1;              % number of MPI processors

% Set discretization parameters, physical parameters, and solver parameters
pde.porder = 3;          % polynomial degree
pde.torder = 2;          % time-stepping order of accuracy
pde.nstage = 2;          % time-stepping number of stages
pde.dt = 0.001*ones(1,20);   % time step sizes
pde.visdt = 0.1; % visualization timestep size
pde.saveSolFreq = 20;          % solution is saved every 10 time steps
pde.soltime = 20:20:length(pde.dt); % steps at which solution are collected

g = 1;   % gravity
k = 1;
H = 5;
A = 0.1;
c02 = 1.0e4;

pde.physicsparam = [g, c02, k, H, A];

pde.tau = 2;  % DG stabilization parameter
pde.GMRESrestart=29;            % number of GMRES restarts
pde.linearsolvertol=1e-12;       % GMRES tolerance
pde.linearsolveriter=30;        % number of GMRES iterations
pde.precMatrixType=2;           % preconditioning type
pde.NLtol = 1e-12;              % Newton tolerance
pde.NLiter=3;                   % Newton iterations

% parameters for differential algebraic equations
pde.dae_alpha = 1.0;
pde.dae_beta = 0.0;

% create a grid of 10 by 10 on the unit square
[mesh.p,mesh.t] = squaremesh(20,10,1,1);
mesh.p(1,:) = 2*pi*mesh.p(1,:);
mesh.p(2,:) = H*mesh.p(2,:) - H;

% expressions for domain boundaries: bottom, right, top, left
mesh.boundaryexpr = {@(p) abs(p(2,:)+H)<1e-6, @(p) abs(p(1,:)-2*pi)<1e-6, @(p) abs(p(2,:))<1e-6, @(p) abs(p(1,:))<1e-6};
%mesh.boundarycondition = [2;1;2;1]; % wall, perioidic, wall, periodic 
% Set periodic boundary conditions
%mesh.periodicexpr = {2, @(p) p(2,:), 4, @(p) p(2,:)};
mesh.boundarycondition = [1;3;2;3]; % wall, perioidic, wall, periodic 
mesh.periodicexpr = {2, @(p) p(2,:), 4, @(p) p(2,:)};

% search compilers and set options
pde = setcompilers(pde);       

% generate input files and store them in datain folder
[pde,mesh,master,dmd] = preprocessing(pde,mesh);

% generate source codes and store them in app folder
gencode(pde); 

% compile source codes to build an executable file and store it in app folder
compilerstr = compilecode(pde);

% % run executable file to compute solution and store it in dataout folder
runstr = runcode(pde);

sol = fetchsolution(pde,master,dmd, 'dataout');

[plocal,tlocal] = masternodes(pde.porder,2,1);
m.plocal = double(plocal);
m.tlocal = double(tlocal);
m.porder = pde.porder;
dgnodes = createdgnodes(mesh.p,mesh.t,mesh.f,mesh.curvedboundary,mesh.curvedboundaryexpr,pde.porder);  
m.p = mesh.p';
m.t = mesh.t';

vidObj = VideoWriter('m.avi');
open(vidObj);

for it = 1:size(sol,4)
    t = 20*0.001*it;
    
    clf;
    u = squeeze(sol(:,7,:,it));
    dg  = dgnodes;
    dg(:,2,:) = dg(:,2,:) + sol(:,7,:,it);
    m.dgnodes = dg;
    
    % Airy wave
    omega  = sqrt(g*k*tanh(k*H));
    
    p = (omega^2/k)*A*cosh(k*(dg(:,2,:)+H)).*cos(k*dg(:,1,:)-omega*t)/sinh(k*H) - g*dg(:,2,:);
    eta = A*sinh(k*(dg(:,2,:)+H)).*cos(k*dg(:,1,:)-omega*t)/sinh(k*H);

scaplot(m,abs(u-squeeze(eta)),[],0,1);
currFrame = getframe(gcf);
writeVideo(vidObj,currFrame);
end

close(vidObj);

%sol(:,7,:,:) = sol(:,5,:,:)-sol(:,4,:,:);
%pde.visscalars = {"eta", 7, "pressure", 8};
%pde.visvectors = {"velocity", [1, 2]};
%vis(sol,pde,mesh);
