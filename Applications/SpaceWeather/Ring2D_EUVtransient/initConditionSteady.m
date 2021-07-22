function UDG = initConditionSteady(mesh,UDG,mu)

gam = mu(1);
gam1 = gam-1;
Re = mu(2);
Pr = mu(3);
Minf = mu(4);
M2 = Minf^2;

Fr2 = mu(5);
omega = mu(6);
Q0 = mu(12);
M0 = mu(13);

rbot = mu(7);
Tbot = mu(8);
Ttop = mu(9);

R0 = mu(10);
R1 = mu(11);
Ldim = mu(14);
vdim = Minf*sqrt(gam*287*200);
Ldim2 = Ldim^2;
Ldim3 = Ldim^3;

% Radial position

nElems = size(mesh.dgnodes,3);
nNodesElem = size(mesh.dgnodes,1);

r_nodes = zeros(nNodesElem*nElems,1);

for iElem = 1:nElems
    xElem = mesh.dgnodes(:,:,iElem);
    r_nodes(nNodesElem*(iElem-1)+1:nNodesElem*iElem) = sqrt(xElem(:,1).^2 + xElem(:,2).^2);
end

r_nodes = uniquetol(r_nodes,1e-5);

%% EUV
%Computation F10.7 (let's assume it constant at first, the variation is at another scale)
    F10p7 = 100;
    F10p7_81 = 100;
    F10p7_mean = 0.5*(F10p7 + F10p7_81);
    

%Computation of the EUV term
rho = @(r) exp(r);
gravity = @(x) Fr2;
% gravity = @(x) Fr2*R0^2/x^2;
H = @(x,T) T./(gam*M2*gravity(x));
a = @(x) -gravity(x) + omega^2*x;

%Chapman integral 
Xp = @(x,T) x./H(x,T);
y0 = @(x,T) sqrt(Xp(x,T)/2)*sqrt(0.5);

Ierf = @(x,T) 0.5*(1+tanh(1000*(8-y0(x,T))));
a_erf = 1.06069630;
b_erf = 0.55643831;
c_erf = 1.06198960;
d_erf = 1.72456090;
f_erf = 0.56498823;
g_erf = 0.06651874;

erfcy = @(x,T) Ierf(x,T).*(a_erf + b_erf*y0(x,T))./(c_erf + d_erf*y0(x,T) + y0(x,T).*y0(x,T)) + (1-Ierf(x,T)).*f_erf./(g_erf + y0(x,T));

alpha = @(x,T,r) rho(r).*H(x,T).*erfcy(x,T).*sqrt(0.5*pi*Xp(x,T));

%Vector of physical EUV parameters
EUV = readtable('euv.csv');
lambda = (0.5*(table2array(EUV(1,6:42))+table2array(EUV(2,6:42))))*1e-10/Ldim;    % initially in Armstrongs
crossSection = (0.78*table2array(EUV(5,6:42))*table2array(EUV(5,4))+0.22*table2array(EUV(8,6:42))*table2array(EUV(5,4)))/Ldim2;   % initially in m2
AFAC = table2array(EUV(4,6:42));                        % non-dimensional
F74113 = table2array(EUV(3,6:42))*table2array(EUV(3,4))*1e4*Ldim3/vdim;                                                 % initially in 1/(cm2*s)


slope0 = 1 + AFAC*(F10p7_mean-80);
Islope = 0.5*(1+tanh(1000*(slope0-0.8)));
slopeIntensity =  slope0.*Islope + 0.8*(1-Islope);
Intensity0 = F74113.*slopeIntensity;

crossSectionM = mean(crossSection);

Q = @(x,T,r) sum(crossSection.*Intensity0./lambda)*exp(-M0*crossSectionM*alpha(x,T,r));
    
H0 = R0 + 65/500*(R1-R0);
eff0 = @(x) 0.6 - 5.54e-11*(Ldim*(x-H0)).^2;
Ieff = @(x) 0.5*(1+tanh(1000*(eff0(x)-0.2)));
eff = @(x) 0.2 + (eff0(x)-0.2).*Ieff(x);

s_EUV = @(x,T,r) gam*gam1*M2*eff(x)*Q0.*Q(x,T,r);


%%

% kappa = @(T) T^0.75;
% dkappadT = @(T) 0.75*T^(-0.25);
kappa = @(T) 1;
dkappadT = @(T) 0;


% f = @(x,y) [y(2); -s_EUV(x,y(1),y(3))./kappa(y(1)) - dkappadT(y(1)).*y(2).*y(2)./kappa(y(1)) - y(2)./x; -y(2)./y(1) + gam*M2*a(x)./y(1)];
% f = @(x,y) [y(2); -(y(2)./(x)  + y(2).*(gam*M2*a(x) - y(2))./y(1) + dnudT(y(1)).*y(2).^2./nu(y(1)) + Re*Pr./(gam*nu(y(1))).*s_EUV(x,y(1),y(3))); (gam*M2*a(x) - y(2))./y(1)];
% f = @(x,y) [y(2); -y(2)./x - Re*Pr./(gam*nu(y(1),y(3))).*s_EUV(x,y(1),y(3)) - dmudT(y(1)).*y(2).^2./(mu(y(1))); (gam*M2*a(x) - y(2))./y(1)];
f = @(x,y) [y(2); -y(2)./x - dkappadT(y(1)).*y(2).^2./kappa(y(1)) - Re*Pr*rho(y(3)).*s_EUV(x,y(1),y(3))./(gam*kappa(y(1))); (gam*M2*a(x)-y(2))./y(1)];

q0m = 0.4;  q0p = 0.6;

opts_1 = odeset('RelTol',1e-12,'AbsTol',1e-14);
[~,ym] = ode45(@(x,y) f(x,y),[R0,R1],[Tbot; q0m; rbot],opts_1);
[~,yp] = ode45(@(x,y) f(x,y),[R0,R1],[Tbot; q0p; rbot],opts_1);

%secant
qn = 0.5*(q0m + q0p);
[xn,yn] = ode45(@(x,y) f(x,y),[R0,R1],[Tbot; qn; rbot,],opts_1);
cond = yn(end,2);
% cond = yn(end,1)-Ttop;
while abs(cond)>1e-10
    if cond<0
        q0m = qn;
    else
        q0p = qn;
    end
    
    qn = 0.5*(q0m + q0p);
    [xn,yn] = ode45(@(x,y) f(x,y),[R0,R1],[Tbot; qn; rbot],opts_1);
    cond = yn(end,2);
%     cond = yn(end,1)-Ttop;
end

% addpath('../../../Version0.1/Matlab/export_fig')
% figure
% plot(xn,yn(:,1),'LineWidth',2)
% xlabel('$r$','Fontsize',18,'interpreter','latex')
% ylabel('$T$','Fontsize',18,'interpreter','latex')
% set(gca,'TickLabelInterpreter','latex','FontSize',16)
% axis([R0-1 R1 min(yn(:,1)) max(yn(:,1))+0.1])
% grid on
% % % export_fig 'Plots/Re3000_T.pdf' -r700
% % 
% figure
% plot(xn,yn(:,3),'LineWidth',2)
% xlabel('$r$','Fontsize',18,'interpreter','latex')
% ylabel('$\bar{\rho}$','Fontsize',18,'interpreter','latex')
% set(gca,'TickLabelInterpreter','latex','FontSize',16)
% axis([R0-1 R1 min(yn(:,3))-0.1 max(yn(:,3))+0.1])
% grid on
% % export_fig 'Plots/Re3000_rho.pdf' -r700


gradR = (gam*M2*a(xn)-yn(2))./yn(1);

for iElem = 1:nElems
    for iNode = 1:nNodesElem
        x1 = mesh.dgnodes(iNode,1,iElem);
        x2 = mesh.dgnodes(iNode,2,iElem);
        r = sqrt(x1^2 + x2^2);

        [~,indexR] = min(abs(xn - r));

        UDG(iNode,1,iElem) = yn(indexR,3);
        UDG(iNode,4,iElem) = yn(indexR,1);
%         
%         UDG(iNode,5,iElem) = -gradR(indexR)*x1/r;
%         UDG(iNode,9,iElem) = -gradR(indexR)*x2/r;
%         UDG(iNode,8,iElem) = -yn(indexR,2)*x1/r;
%         UDG(iNode,12,iElem) = -yn(indexR,2)*x2/r;
    end
end
