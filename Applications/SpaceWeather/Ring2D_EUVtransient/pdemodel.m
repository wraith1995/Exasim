function pde = pdemodel
pde.mass = @mass;
pde.flux = @flux;
pde.source = @source;
pde.fbou = @fbou;
pde.ubou = @ubou;
pde.initu = @initu;
end

function m = mass(u, q, w, v, x, t, mu, eta)
m = sym([1.0; 1.0; 1.0; 1.0]); 
end

function f = flux(u, q, w, v, x, t, mu, eta)
    gam = mu(1);
    gam1 = gam - 1.0;
    Re = mu(2);
    Pr = mu(3);
    Minf = mu(4);
    visc = 1/Re;
    M2 = Minf^2;
    c23 = 2.0/3.0;
    
    r = u(1);
    uv = u(2);
    vv = u(3);
    T = u(4);
    
    rx = q(1);
    ux = q(2);
    vx = q(3);
    Tx = q(4);
    ry = q(5);
    uy = q(6);
    vy = q(7);
    Ty = q(8);
    
    rho = exp(r);
    r1 = 1/rho;
    p = r*T/(gam*M2);

    fi = [r*uv, uv*uv+p, vv*uv, uv*T, ...
            r*vv, uv*vv, vv*vv+p, vv*T];
        
    % Viscosity
%     nu = visc;
%     kstar = T^0.75;
    kstar = 1;
    nu = visc*r1;
    fc = kstar*gam*nu/Pr;
    
    txx = nu*c23*(2*ux - vy);
    txy = nu*(uy + vx);
    tyy = nu*c23*(2*vy - ux);
    
    fv = [0, txx, txy, fc*Tx, ...
          0, txy, tyy, fc*Ty];
    f = fi+fv;
    f = reshape(f,[4,2]);    
end

function s = source(u, q, w, v, x, t, mu, eta)
    gam = mu(1);
    gam1 = gam - 1.0;
    Re = mu(2);
    Pr = mu(3);
    Minf = mu(4);
    visc = 1/Re;
    M2 = Minf^2;
    c23 = 2.0/3.0;
    
    r = u(1);
    uv = u(2);
    vv = u(3);
    T = u(4);
    
    rx = -q(1);
    ux = -q(2);
    vx = -q(3);
    Tx = -q(4);
    ry = -q(5);
    uy = -q(6);
    vy = -q(7);
    Ty = -q(8);
    
    rho = exp(r);
    r1 = 1/rho;
        
%     kstar = T^0.75;
    kstar = 1;
    nu = visc*r1;
    fc = kstar*gam*nu/Pr;
    
    txx = nu*c23*(2*ux - vy);
    txy = nu*(uy + vx);
    tyy = nu*c23*(2*vy - ux);

    r_1 = r-1;

    z = sqrt(x(1)^2 + x(2)^2);
    
    R0 = mu(10);
    gravity0 = mu(5);
    gravity = gravity0*R0^2/(z^2);
    omega = mu(6);
    ax = -gravity*x(1)/z + 2*omega*vv + x(1)*omega^2;
    ay = -gravity*x(2)/z - 2*omega*uv + x(2)*omega^2;
    
    div = ux + vy;
    Tdrx = txx*rx + txy*ry;
    Tdry = txy*rx + tyy*ry;
    TdV = (txx*ux + txy*uy + txy*vx + tyy*vy)*(gam*gam1*M2);
    drdT = fc*(rx*Tx + ry*Ty);
    
    s_EUV = EUVsource(u, x, t, mu, eta);
    
    %sponge layer
    sigma = v;
    vr = (uv*x(1) + vv*x(2))/z;
    f_spongeU = -sigma*vr*x(1)/z;
    f_spongeV = -sigma*vr*x(2)/z;
%     f_spongeU = -sigma*uv;
%     f_spongeV = -sigma*vv;
    
    s = [r_1*div; ...
        ax + div*uv + r_1*Tx/(gam*M2) + Tdrx + f_spongeU; ...
        ay + div*vv + r_1*Ty/(gam*M2) + Tdry + f_spongeV; ...
        s_EUV + (2-gam)*T*div + drdT + TdV];
end

function fb = fbou(u, q, w, v, x, t, mu, eta, uhat, n, tau)
    f = flux(u, q, w, v, x, t, mu, eta);
    fh = f(:,1)*n(1) + f(:,2)*n(2) + tau*(u-uhat); % numerical flux at freestream boundary
    fw = fh;
    fw(1) = 0.0;   % zero velocity 
    
    % Inviscid wall
    ft = fw;
    ft(4) = 0.0;
    
    fb = [fw ft];
end

function ub = ubou(u, q, w, v, x, t, mu, eta, uhat, n, tau)
    Tbot = mu(8);

    % Isothermal Wall?
    utw1 = u;
    utw1(2:3) = 0.0;
    utw1(4) = Tbot;

    % Inviscid wall
    utw2 = u;
    vn = u(2)*n(1) + u(3)*n(2);
    utw2(2) = u(2) - vn*n(1);
    utw2(3) = u(3) - vn*n(2);
    
    ub = [utw1 utw2];
end


function u0 = initu(x, mu, eta)
    gam = mu(1);
    Minf = mu(4);
    M2 = Minf^2;
    gravity = mu(5);
    rbot = mu(7);
    Tbot = mu(8);
    R0 = mu(10);
    R1 = mu(11);
    H0 = R1-R0;
    z = (sqrt(x(1)^2 + x(2)^2)-R0);
    
    r = rbot - gam*M2*gravity*z/Tbot;
    u0 = [r, 0.0, 0.0, Tbot];    
end
