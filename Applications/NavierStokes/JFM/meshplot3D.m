function meshplot3D(p,t,tmarks)

p = p/6000;

clf;

vis = sum(p.^2,1) < 9;
tvis = prod(vis(t),1);

pars = {'facecolor',[0.8,1.0,0.8],'edgecolor','k','Linew',1,'FaceAlpha',1,'EdgeAlpha',1};
patch('faces',t(:,tvis == 1)','vertices',p',pars{:}); grid on; hold on;

axis equal;