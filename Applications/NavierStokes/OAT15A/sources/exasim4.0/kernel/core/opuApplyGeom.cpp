#ifndef __OPUAPPLYGEOM
#define __OPUAPPLYGEOM

template <typename T> void opuApplyJac(T *sg, T *fhg, T *jac, int nga, int ncu, int ngf)
{
    int M = ngf*ncu;
    int N = nga*ncu;
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%nga;   
        int m = (idx-i)/nga; // [1, ncu]
        int g = i%ngf;       // [1, ngf]
        int e = (i-g)/ngf;   // [1, nf]                
        sg[g+ngf*m+M*e] = fhg[idx]*jac[i];
    }
}

template <typename T> void opuApplyJac1(T *sg, T *jac, int nga, int ncu)
{
    int N = nga*ncu;
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%nga;        
        sg[idx] = sg[idx]*jac[i];
    }
}

template <typename T> void opuApplyJac2(T *sg, T *jac, T *ug, T *su, T *fc_u, int nga, int ncu)
{
    int N = nga*ncu;
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%nga;        
        int n = (idx-i)/nga;
        sg[idx] = (sg[idx] + su[idx] - ug[idx]*fc_u[n])*jac[i];
    }    
}

template <typename T> void opuApplyXx1(T *sg, T *ug, T *Xx, int nga, int nd, int ncu)
{
    int N = nga*ncu;
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%nga;        
        sg[idx] = ug[idx]*Xx[i];
    }    
}

template <typename T> void opuApplyXx2(T *sg, T *fg, T *Xx, int nga, int nd, int ncu)
{
    int N = nga*ncu;

    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%nga;        
        sg[idx] = 0.0;
        for (int j=0; j<nd; j++)
            sg[idx] = sg[idx] + fg[idx+N*j]*Xx[i+nga*j];
    }        
}

template <typename T> void opuApplyXx3(T *sg, T *ug, T *Xx, int nge, int nd, int ncu, int ne)
{
    int M = nge*ne;
    int N = M*ncu;
    int P = M*nd;
    int I = nge*nd;
    int J = I*ncu;
    int K = J*nd;
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%M;       // [1, nge*ne]         
        int k = (idx-i)/M;   // [1, ncu]
        int g = i%nge;       // [1, nge]
        int e = (i-g)/nge;   // [1, ne]
        for (int m=0; m<nd; m++)
            for (int j=0; j<nd; j++)
                sg[g+nge*j+I*k+J*m+K*e] = ug[idx]*Xx[g+nge*e+M*m+P*j];
    }    
}

template <typename T> void opuApplyXx4(T *rg, T *sg, T *fg, T *Xx, T *jac, int nge, int nd, int ncu, int ne)
{
    int M = nge*ne;
    int N = M*ncu;
    int P = M*nd;
    int I = nge*(nd+1);
    int J = I*ncu;
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%M;       // [1, nge*ne]         
        int k = (idx-i)/M;   // [1, ncu]
        int g = i%nge;       // [1, nge]
        int e = (i-g)/nge;   // [1, ne]
        // idx = g + nge*e + nge*ne*k
        rg[g+nge*0+I*k+J*e] = sg[idx]*jac[i];        
        for (int m=0; m<nd; m++) {
            rg[g+nge*(m+1)+I*k+J*e] = fg[idx+N*0]*Xx[g+nge*e+M*0+P*m];
            for (int j=1; j<nd; j++)
                rg[g+nge*(m+1)+I*k+J*e] += fg[idx+N*j]*Xx[g+nge*e+M*j+P*m];
        }
    }    
}

template <typename T> void opuApplyXx5(T *rg, T *fg, T *Xx, int nge, int nd, int ncu, int ne)
{
    int M = nge*ne;
    int N = M*ncu;
    int P = M*nd;
    int I = nge*(nd+1);
    int J = I*ncu;
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%M;       // [1, nge*ne]         
        int k = (idx-i)/M;   // [1, ncu]
        int g = i%nge;       // [1, nge]
        int e = (i-g)/nge;   // [1, ne]
        // idx = g + nge*e + nge*ne*k
        for (int m=0; m<nd; m++) {
            rg[g+nge*m+I*k+J*e] = fg[idx+N*0]*Xx[g+nge*e+M*0+P*m];
            for (int j=1; j<nd; j++)
                rg[g+nge*m+I*k+J*e] += fg[idx+N*j]*Xx[g+nge*e+M*j+P*m];
        }
    }    
}

template <typename T> void opuApplyJacNormal(T *fqg, T *uhg, T *nlg, T *jac, int nga, int ncu, int nd)
{
    int N = nga*ncu;
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%nga;                
        for (int j=0; j<nd; j++)
            fqg[idx+N*j] = uhg[idx]*nlg[i+nga*j]*jac[i];
    }            
}

template <typename T> void opuApplyJacNormal(T *fqg, T *uhg, T *nlg, T *jac, int nga, int ncu, int nd, int ngf)
{
    int N = nga*ncu;
    int M = ngf*ncu;
    int P = M*nd; 
    for (int idx = 0; idx<N; idx++)
    {
        int i = idx%nga;   
        int m = (idx-i)/nga; // [1, ncu]
        int g = i%ngf;       // [1, ngf]
        int e = (i-g)/ngf;   // [1, nf]
        for (int j=0; j<nd; j++)
            fqg[g+ngf*m+M*j+P*e] = uhg[idx]*nlg[i+nga*j]*jac[i];
    }            
}

template <typename T> void opuApplyFactor(T *Rfac, T *R, T *fac, int npe, int M, int N)
{
    // N = npe*ncr*ne
    // M = npe*ncr
    // R:   [npe*ncr*ne]
    // fac: [ncr]    
    for (int n=0; n<N; n++) {
        int m = n%M;       // [1, npe*ncr] 
        int k = m%npe;     // [1, npe]
        int j = (m-k)/npe; // [1, ncr]
        Rfac[n] = R[n]/fac[j];
    }            
}

template <typename T> void opuApplyJac(T *Rfac, T *R, T *jac, int M, int N)
{
    // M = npe*ncr
    // N = npe*ncr*ne
    // R:   [npe*ncr*ne]
    // jac: [ne]    
    for (int n=0; n<N; n++) {            
        int m = n%M;       // [1, npe*ncr] 
        int i = (n-m)/M;   // [1, ne] 
        Rfac[n] = R[n]*(jac[i]);
    }                        
}

template <typename T> void opuApplyJacInv(T *Rfac, T *R, T *jac, int M, int N)
{
    // M = npe*ncr
    // N = npe*ncr*ne
    // R:   [npe*ncr*ne]
    // jac: [ne]    
    for (int n=0; n<N; n++) {            
        int m = n%M;       // [1, npe*ncr] 
        int i = (n-m)/M;   // [1, ne] 
        Rfac[n] = R[n]/(jac[i]);
    }                        
}

template <typename T> void opuApplyFactorJac(T *Rfac, T *R, T *fac, T *jac, int npe, int M, int N)
{
    // M = npe*ncr
    // N = npe*ncr*ne
    // R:   [npe*ncr*ne]
    // fac: [ncr]    
    // jac: [ne]    
    for (int n=0; n<N; n++) {            
        int m = n%M;       // [1, npe*ncr] 
        int i = (n-m)/M;   // [1, ne] 
        int k = m%npe;     // [1, npe]
        int j = (m-k)/npe; // [1, ncr]
        Rfac[n] = R[n]/(fac[j]*jac[i]);
    }                        
}

template <typename T> void opuShapJac(T *shapjac, T *shapegt, T *jac, int nge, int M, int N)
{
    // M = nge*npe
    // N = nge*npe*ne
    for (int i=0; i<N; i++) {                                            
        int l = i%M;       // [1, nge*npe]           
        int k = (i-l)/M;   // [1, ne] 
        int n = l%nge;     // [1,nge]
        int m = (l-n)/nge; // [1, npe]
        shapjac[i] = shapegt[n+nge*m]*jac[n+nge*k];
    }    
}

template void opuApplyJac(double*, double*, double*, int, int, int);
template void opuApplyJac1(double*, double*, int, int);
template void opuApplyJac2(double*, double*, double*, double*, double*, int, int);
template void opuApplyXx1(double*, double*, double*, int, int, int);
template void opuApplyXx2(double*, double*, double*, int, int, int);
template void opuApplyXx3(double*, double*, double*, int, int, int, int);
template void opuApplyXx4(double*, double*, double*, double*, double*, int, int, int, int);
template void opuApplyXx5(double*, double*, double*, int, int, int, int);
template void opuApplyJacNormal(double*, double*, double*, double*, int, int, int);    
template void opuApplyJacNormal(double*, double*, double*, double*, int, int, int, int);    
template void opuApplyFactor(double*, double*, double*, int, int, int);
template void opuApplyFactorJac(double*, double*, double*, double*, int, int, int);
template void opuApplyJacInv(double*, double*, double*, int, int);
template void opuApplyJac(double*, double*, double*, int, int);
template void opuShapJac(double*, double*, double*, int, int, int);

template void opuApplyJac(float*, float*, float*, int, int, int);
template void opuApplyJac1(float*, float*, int, int);
template void opuApplyJac2(float*, float*, float*, float*, float*, int, int);
template void opuApplyXx1(float*, float*, float*, int, int, int);
template void opuApplyXx2(float*, float*, float*, int, int, int);
template void opuApplyXx3(float*, float*, float*, int, int, int, int);
template void opuApplyXx4(float*, float*, float*, float*, float*, int, int, int, int);
template void opuApplyXx5(float*, float*, float*, int, int, int, int);
template void opuApplyJacNormal(float*, float*, float*, float*, int, int, int);    
template void opuApplyJacNormal(float*, float*, float*, float*, int, int, int, int);    
template void opuApplyFactor(float*, float*, float*, int, int, int);
template void opuApplyFactorJac(float*, float*, float*, float*, int, int, int);
template void opuApplyJacInv(float*, float*, float*, int, int);
template void opuApplyJac(float*, float*, float*, int, int);
template void opuShapJac(float*, float*, float*, int, int, int);

#endif

