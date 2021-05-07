function [p,t,dgnodes] = mkmesh_ring_scaleheight(porder,R0,R1,T0,T1,g0,omega,R,rate,AR)
% Generates mesh on the ring defining the elements assuming constant pressure ratio.

elemtype = 1;

% R0b = R0+100;
% I200 = @(r) 0.5*(1+tanh(1000*(r-R0b)));
% T = @(r) T1*I200(r) + (T0 + (T1-T0)*(r-R0)/(R0b-R0)).*(1-I200(r));

T = @(r) T1 - (T1-T0)*exp(-(r-R0)/40);
g = @(r) g0*R0^2./(r.^2);
dp_p = @(r) -(g(r) - omega^2*r)./(R*T(r));

h = @(x) exp(integral(dp_p,R0,x));
nDivY = floor(log(h(R1))/log(rate));
trueRate = exp(log(h(R1))/nDivY);

yp = zeros(nDivY+1,1);
yp(1) = R0; yp(nDivY+1) = R1;
for iDiv=1:nDivY-1
    hi = @(x) exp(integral(dp_p,yp(iDiv),x)) - trueRate;
    yn = fsolve(hi,yp(iDiv));
    yp(iDiv+1) = yn;
end

nDivX = floor(2*pi*R0/(AR*(yp(2)-R0)));

[p,t] = squaremesh(nDivX-1,nDivY,1,elemtype);
p=p'; 

ln = (yp-R0)/(R1-R0);
ln  = reshape(ones(nDivX,1)*ln',[nDivX*(nDivY+1),1]);


% Assign mesh point positions
p(:,2) = ln;

dgnodes = mkdgnodes(p',t,porder);

pnew = p;
pnew(:,1) = -(R0+(R1-R0)*p(:,2)).*sin(2*pi*p(:,1));
pnew(:,2) = -(R0+(R1-R0)*p(:,2)).*cos(2*pi*p(:,1));
[p,t] = fixmesh(pnew,t');
p = p';
t = t';

pnew = zeros(size(dgnodes));
pnew(:,1,:) = -(R0+(R1-R0)*dgnodes(:,2,:)).*sin(2*pi*dgnodes(:,1,:));
pnew(:,2,:) = -(R0+(R1-R0)*dgnodes(:,2,:)).*cos(2*pi*dgnodes(:,1,:));
dgnodes = pnew;


function dgnodes = mkdgnodes(p,t,porder)
%CREATEDGNODES Computes the Coordinates of the DG nodes.
%   DGNODES=CREATENODES(MESH,FD,FPARAMS)
%
%      MESH:      Mesh Data Structure
%      FD:        Distance Function d(x,y)
%      FPARAMS:   Additional parameters passed to FD
%      DGNODES:   Triangle indices (NPL,2,NT). The nodes on 
%                 the curved boundaries are projected to the
%                 true boundary using the distance function FD
%

% npv : number of nodes per volume element
% nfv : number of faces per volume element
% npf : number of nodes per face element

% if porder>4
%     error("app.porder must be less than or equal to 4.");
% end

[nve,ne]=size(t);
nd=size(p,1);

elemtype = 0;
if (nd==2) && (nve==4)
    elemtype=1;    
end
if (nd==3) && (nve==8)
    elemtype=1;    
end

plocal = masternodes(porder,nd,elemtype);

npl=size(plocal,1);
if nd==1
    xi  = plocal(:,1);
    philocal(:,1) = 1 - xi;
    philocal(:,2) = xi;
elseif nd==2 && nve==3 % tri
    xi  = plocal(:,1);
    eta = plocal(:,2);    
    philocal(:,1) = 1 - xi - eta;
    philocal(:,2) = xi;
    philocal(:,3) = eta;
elseif nd==2 && nve==4 % quad
    xi  = plocal(:,1);
    eta = plocal(:,2);
    philocal(:,1) = (1-xi).*(1-eta);
    philocal(:,2) = xi.*(1-eta);
    philocal(:,3) = xi.*eta;
    philocal(:,4) = (1-xi).*eta;
elseif nd==3 && nve==4 % tet
    xi   = plocal(:,1);
    eta  = plocal(:,2);
    zeta = plocal(:,3);
    philocal(:,1) = 1 - xi - eta - zeta;
    philocal(:,2) = xi;
    philocal(:,3) = eta;
    philocal(:,4) = zeta;
elseif nd==3 && nve==8 % hex
    xi   = plocal(:,1);
    eta  = plocal(:,2);
    zeta = plocal(:,3);
    philocal(:,1) = (1-xi).*(1-eta).*(1-zeta);
    philocal(:,2) = xi.*(1-eta).*(1-zeta);
    philocal(:,3) = xi.*eta.*(1-zeta);
    philocal(:,4) = (1-xi).*eta.*(1-zeta);    
    philocal(:,5) = (1-xi).*(1-eta).*(zeta);
    philocal(:,6) = xi.*(1-eta).*(zeta);
    philocal(:,7) = xi.*eta.*(zeta);
    philocal(:,8) = (1-xi).*eta.*(zeta);        
end
    
% Allocate nodes
dgnodes=zeros(npl,nd,ne);
for dim=1:nd
  for node=1:nve
    dp=reshape(philocal(:,node),[npl 1])*reshape(p(dim,t(node,:)),[1 ne]);
    dgnodes(:,dim,:)=dgnodes(:,dim,:)+reshape(dp,[npl 1 ne]);
  end
end
