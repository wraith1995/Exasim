function mesh = spongeLayerMesh(mesh,pde,maxVDG)

dgnodes = mesh.dgnodes;
R1 = pde.physicsparam(11);
R1phys = pde.physicsparam(15);

nNodesElem = size(dgnodes,1);
nOfElems = size(dgnodes,3);
mesh.vdg = zeros(nNodesElem,1,nOfElems);
rDGelem = zeros(nNodesElem,1,nOfElems);

Rmin = 1e10;
Rmax = 0;

for iElem = 1:nOfElems
   xDGelem = dgnodes(:,:,iElem);
   rDGelem(:,1,iElem) = sqrt(xDGelem(:,1).^2 + xDGelem(:,2).^2);
   
   if min(rDGelem(:,1,iElem))>R1phys-1e-1
       Rmin = min(Rmin,min(rDGelem(:,1,iElem)));
       Rmax = max(Rmax,max(rDGelem(:,1,iElem)));
       mesh.vdg(:,:,iElem) = maxVDG; 
   end
end

deltaR = Rmax-Rmin;
mesh.vdg = mesh.vdg.*((rDGelem-Rmin)/deltaR);

% for iElem = 1:nOfElems
%    if min(rDGelem(:,1,iElem))-1e-1<Rmin
%        Rmax = max(rDGelem(:,1,iElem));
%        deltaR = Rmax-Rmin;
%        mesh.vdg(:,:,iElem) = mesh.vdg(:,:,iElem).*((rDGelem(:,1,iElem)-Rmin)/deltaR);
%    end
% end


% for iElem = 1:nOfElems
%    if mesh.vdg(:,:,iElem)
%        deltaR = Rmax-Rmin;
%        mesh.vdg(:,:,iElem) = maxVDG*(rDGelem(:,iElem)-Rmin)/deltaR;
%    end
% end