# Poisson equation with homogenous Dirichlet condition on a unit square
# q + \nabla u = 0 in \Omega
# \nabla dot flux = source in \Omega
# u = 0 on \partial Omega
# flux = 2*param*q
# source = 2*pi*pi*sin(pi*x1)*sin(pi*x2);

from numpy import array
from sympy import sin, pi

def flux(u, q, w, v, x, t, mu, eta):
    f = mu*q;
    return f;

def source(u, q, w, v, x, t, mu, eta):
    s = array([1.0]);
    return s;

def fbou(u, q, w, v, x, t, mu, eta, uhat, n, tau):
    f = flux(u, q, w, v, x, t, mu, eta);
    fb = array([f[0]*n[0] + f[1]*n[1] + tau[0]*(u[0]-0.0)]);
    return fb;

def ubou(u, q, w, v, x, t, mu, eta, uhat, n, tau):
    ub = array([0.0]);
    return ub;

def initu(x, mu, eta):
    u0 = array([0.0]);
    return u0;