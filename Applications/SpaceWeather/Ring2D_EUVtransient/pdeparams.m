function [pde, mesh] = pdeparams(pde,mesh)

% Define a PDE model: governing equations, initial solutions, and boundary conditions
pde.model = "ModelD";          % ModelC, ModelD, ModelW
pde.modelfile = "pdemodel";    % name of a file defining the PDE model

% Set discretization parameters, physical parameters, and solver parameters
pde.porder = 2;          % polynomial degree
pde.torder = 2;          % time-stepping order of accuracy
pde.nstage = 2;          % time-stepping number of stages
pde.dt = 0.02*ones(10000,1);   % time step sizes
pde.visdt = pde.dt(1);         % visualization timestep size
pde.saveSolFreq = 50;          % solution is saved every 100 time steps
pde.soltime = 50:50:length(pde.dt); % steps at which solution are collected
pde.timestepOffset = 0;

% Nondimensional constants
gam = 5/3;                      % specific heat ratio
Re = 10e3;                      % Reynolds number
Pr = 0.3;                      % Prandtl number    
Minf = 0.1;                     % Mach number

%Physical quantities
R0dim = 6470000;
R1physicalDim = 6970000;
R1boundaryDim = R1physicalDim + 0*(R1physicalDim-R0dim);
rhodim = 6.6e-7;
Tdim = 200;
Rdim = 287;
gdim = 9.5;
omega = 2*pi/86400;
h = 6.0626e-34;
c = 3e8;
m = 28.9*1.66e-27;

Ldim = Rdim*Tdim/gdim;
vdim = Minf*sqrt(gam*Rdim*Tdim);

vdim2 = vdim^2;
Ldim2 = Ldim^2;
Ldim3 = Ldim^3;

R0 = R0dim/Ldim;
R1 = R1boundaryDim/Ldim;
R1extra = R1physicalDim/Ldim;

%Nondimensionalized quantities
rbot = 0;                    % Density bottom boundary
Tbot = 1;                     % Temperature bottom surface
Ttop = 6;                     % Temperature top surface (equal to Tbot to start)

%Additional nondimensional numbers
Fr2 = gdim*Ldim/vdim2;                  % Normalized gravity acceleration
St = omega*Ldim/vdim;                   % angular velocity
Q0 = h*c/(m*vdim2*Ldim);
M0 = rhodim*Ldim3/m;

spongeMax = 0;

%Vector of physical parameters
pde.physicsparam = [gam Re Pr Minf Fr2 St rbot Tbot Ttop R0 R1 Q0 M0 Ldim R1extra spongeMax];
                   % 1  2  3   4    5  6   7    8    9   10 11 12 13  14    15

%Vector of physical EUV parameters
EUV = readtable('euv.csv');
lambda = (0.5*(table2array(EUV(1,6:42))+table2array(EUV(2,6:42))))*1e-10/Ldim;    % initially in Armstrongs
crossSections = (0.78*table2array(EUV(5,6:42))*table2array(EUV(5,4))+0.22*table2array(EUV(8,6:42))*table2array(EUV(5,4)))/Ldim2;   % initially in m2
AFAC = table2array(EUV(4,6:42));                        % non-dimensional
F74113 = table2array(EUV(3,6:42))*table2array(EUV(3,4))*1e4*Ldim3/vdim;                                                 % initially in 1/(cm2*s)
pde.externalparam = [lambda,crossSections,AFAC,F74113];
                                      
%Solver parameters
pde.extStab = 1;
pde.tau = 500.0;                  % DG stabilization parameter
pde.GMRESrestart=29;            % number of GMRES restarts
pde.linearsolvertol=1e-10;     % GMRES tolerance
pde.linearsolveriter=30;        % number of GMRES iterations
pde.precMatrixType=2;           % preconditioning type
pde.NLtol = 1e-7;               % Newton toleranccd dataoue
pde.NLiter = 3;                 % Newton iterations

%% Grid
[mesh.p,mesh.t, mesh.dgnodes] = mkmesh_ring(pde.porder,361,51,R0,R1,1.5);
% expressions for domain boundaries
mesh.boundaryexpr = {@(p) abs(p(1,:).^2+p(2,:).^2-R0^2)<1e-6, @(p) abs(p(1,:).^2+p(2,:).^2-R1^2)<1e-6};
mesh.boundarycondition = [1 2];  % Inner, Outer
% expressions for curved boundaries
mesh.curvedboundary = [1 1];
mesh.curvedboundaryexpr = {@(p) sqrt(p(1,:).^2+p(2,:).^2)-R0, @(p) sqrt(p(1,:).^2+p(2,:).^2)-R1};

% angle = 5;
% [mesh.p,mesh.t, mesh.dgnodes] = mkmesh_sector(pde.porder,50,80,R0,R1,angle,1);
% % expressions for domain boundaries
% %mesh.boundaryexpr = {@(p) abs(sqrt(sum(p.^2,1))-R0)<1e-8, @(p) abs(sqrt(sum(p.^2,1))-R1)<1e-8};
% mesh.boundaryexpr = {@(p) abs(p(1,:).^2+p(2,:).^2-R0^2)<1e-6,@(p) (tand(90-angle/2)*p(1,:) - p(2,:))<1e-6, @(p) abs(p(1,:).^2+p(2,:).^2-R1^2)<1e-6, @(p) -(p(2,:) + tand(90+angle/2)*p(1,:))<1e-6};
% mesh.boundarycondition = [1 3 2 3];  % Inner, Outer
% % mesh.periodix =cexpr = {2, @(p) p(1,:).^2 + p(2,:).^2, 4, @(p) p(1,:).^2 + p(2,:).^2};
% % expressions for curved boundaries
% mesh.curvedboundary = [0 0 0 0];
% mesh.curvedboundaryexpr = {@(p) sqrt(p(1,:).^2+p(2,:).^2)-R0,@(p) p(2,:) - tand(90-angle/2)*p(1,:), @(p) sqrt(p(1,:).^2+p(2,:).^2)-R1, @(p) p(2,:) - tand(90+angle/2)*p(1,:)};

