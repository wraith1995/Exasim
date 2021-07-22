function   tau = gettau(uhat, mu, eta,  n)

    gam = mu(1);
    Re = mu(2);
    Pr = mu(3);
    Minf = mu(4);
    
    r = uhat(1);
    uv = uhat(2);
    vv = uhat(3);
    T = uhat(4);
    rho = exp(r);
    r1 = 1/rho;
    
    vn = uv*n(1) + vv*n(2);
    c = sqrt(T)/Minf;
    tauA = abs(vn) + c;
    
    mustar = 1;
    kstar = 1;
    tauDv = mustar*r1/Re;
    tauDT = kstar*gam*tauDv/Pr;
    
    tau = 0*uhat;

    tau(1) = 500;
    tau(2) = 500;% + tauDv;
    tau(3) = 500;% + tauDv;
    tau(4) = 500;% + tauDT;

end