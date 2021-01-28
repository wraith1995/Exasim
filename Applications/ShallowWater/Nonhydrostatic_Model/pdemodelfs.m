function pde = pdemodelfs
pde.mass = @mass;
pde.flux = @flux;
pde.source = @source;
pde.sourcew = @sourcew;
pde.fbou = @fbou;
pde.ubou = @ubou;
pde.initu = @initu;
pde.initw = @initw;
end

function m = mass(u, q, w, v, x, t, mu, eta)
m = sym([1.0; 1.0]); 
end

function f = flux(u, q, w, v, x, t, mu, eta)
    p = w(2);  % pressure   
    f = [p, 0, 0, p];
    f = reshape(f,[2,2]);    
end

function s = source(u, q, w, v, x, t, mu, eta)
g = mu(1); 
s = [sym(0.0); -g];
end

function s = sourcew(u, q, w, v, x, t, mu, eta) 
c02 = mu(2);
s = [u(2); c02*(q(1)+q(4))];
end

function fb = fbou(u, q, w, v, x, t, mu, eta, uhat, n, tau)

%f = flux(u, q, w, v, x, t, mu, eta);
%fw = f(:,1)*n(1) + f(:,2)*n(2) + tau*(u-uhat);

p = w(2);
fw = [p*n(1); p*n(2)];
fw = fw + tau*(u-uhat);

p = mu(1)*w(1);
ff = [p*n(1); p*n(2)];

fb = [fw ff];
end

function ub = ubou(u, q, w, v, x, t, mu, eta, uhat, n, tau)

uw = [u(1); 0.0];
uf = [u(1); u(2)];

ub = sym([uw uf]); 
end

function u0 = initu(x, mu, eta)

    g   = mu(1);
    c02 = mu(2);
    k   = mu(3);
    H   = mu(4);
    A   = mu(5);

    t = 0;
    
    x1 = x(1);
    x2 = x(2);
    
    % Airy wave
    omega  = sqrt(g*k*tanh(k*H));
    
    uv = omega*A*cosh(k*(x2+H))*cos(k*x1-omega*t)/sinh(k*H);
    wv = omega*A*sinh(k*(x2+H))*sin(k*x1-omega*t)/sinh(k*H);
    
    u0 = [uv; wv];
end

function w0 = initw(x, mu, eta)

    g   = mu(1);
    c02 = mu(2);
    k   = mu(3);
    H   = mu(4);
    A   = mu(5);
    
    t = 0;

    x1 = x(1);
    x2 = x(2);
    
    % Airy wave
    omega  = sqrt(g*k*tanh(k*H));
    
    p = (omega^2/k)*A*cosh(k*(x2+H))*cos(k*x1-omega*t)/sinh(k*H) + g*x2;
    eta = A*sinh(k*(x2+H))*cos(k*x1-omega*t)/sinh(k*H);
    
    w0 = [eta; p];
 
end


