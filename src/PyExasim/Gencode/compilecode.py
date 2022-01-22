from numpy import *
from sys import platform
import logging
import subprocess
import sys
import os
import shutil

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-6s %(message)s')
log = logging.getLogger()

def check_call(arguments):
    try:
        log.debug("Running command '%s'", " ".join(arguments))
        log.debug(subprocess.check_output(arguments, stderr=subprocess.STDOUT, shell=shell, env=os.environ).decode())
    except subprocess.CalledProcessError as e:
        log.debug(e.output.decode())
        raise

def compilefiles(compiler, target, srcfile, dflags=[],srcobjects=[], flags=[], ocompilerflags=[]):
    args = [compiler] + dflags + ["-c"] + ocompilerflags + [srcfile]
    args += ["-o", target] + srcobjects
    args += flags
    check_call(args)

def compilecode1(app):
    srcdir = app["srcdir"] + "/"
    osname = app["OS"]
    driverdir = srcdir + "src/Kernel/AppDriver/"
    libdir = srcdir + "lib/" + osname + "/"
    maindir = srcdir + "src/Kernerl/Main/"
    mainfile = maindir + "main.cpp"
    applicationdir = app["appdir"] + "/"
    
    log.info("Compiling Code in {0}".format(applicationdir))
    
    codename = app['codename']    
    version = app['version']
    appname = app['appname']
    cpucompiler = app['cpucompiler']
    mpicompiler = app['mpicompiler']
    gpucompiler = app['gpucompiler']
    enzyme = app['enzyme']
    cpuflags = app['cpuflags']
    gpuflags = app['gpuflags']
    mpiprocs = app['mpiprocs']


    log.info("Copying needed files from src dir ({0})".format(srcdir))
    
    shutil.copyfile(driverdir  + "opuApp.cpp", applicationdir + "opuApp.cpp")
    shutil.copyfile(driverdir  + "cpuApp.cpp", applicationdir + "cpuApp.cpp")
    shutil.copyfile(driverdir  + "gpuApp.cpp", applicationdir + "gpuApp.cpp")

    log.info("Copying object files from lib dir ({0})".format(libdir))
    shutil.copyfile(libdir + "commonCore.o", applicationdir + "commonCore.o")
    shutil.copyfile(libdir + "opuCore.o", applicationdir + "opuCore.o")
    if gpucompiler is not "":
        shutil.copyfile(libdir + "gpuCore.o", applicationdir + "gpuCore.o")
    
    
    log.info("Compiling opuApp.cpp")
    compilefiles(cpucompiler, "opuApp.o", "opuApp.cpp", flags=cpuflags)
    if app['platform'] == "cpu":
        info.log("Compiling for cpu")
        if mpiprocs == 1:
            compilefiles(cpucompiler, "serial" + appname, mainfile, flags=cpuflags + ["--std=c++"], srcobjects=["commonCore.o", "opuCore.o", "opuApp.o"])
            pass
        else:
            pass
    
    
    


def compilecode(app):

    print("compile code...");

    os.chdir("app");

    codename = app['codename'];
    version = app['version'];
    appname = app['appname'];
    cpucompiler = app['cpucompiler'];
    mpicompiler = app['mpicompiler'];
    gpucompiler = app['gpucompiler'];
    enzyme = app['enzyme'];
    cpuflags = app['cpuflags'];
    gpuflags = app['gpuflags'];

    # current directory
    cdir = os.getcwd();
    ii = cdir.find(codename)
    up = cdir[(ii+1):].count("/");
    codedir = "";
    for i in range(0,up):
        codedir = codedir + "../";

    if platform == "darwin":
        coredir = codedir + "lib/Mac/";
    elif platform == "linux" or platform == "linux2":
        coredir = codedir + "lib/Linux/";
    elif platform == "win32":
        coredir = codedir + "lib/Windows/";

    versiondir = codedir  + version;
    appdriverdir = versiondir + "/Kernel/AppDriver/";
    maindir = versiondir + "/Kernel/Main/";

    shutil.copyfile(appdriverdir + "opuApp.cpp", cdir + "/opuApp.cpp");
    shutil.copyfile(appdriverdir + "cpuApp.cpp", cdir + "/cpuApp.cpp");
    shutil.copyfile(appdriverdir + "gpuApp.cu", cdir + "/gpuApp.cu");

    compilerstr = ["" for i in range(12)]

    if  size(cpucompiler)>0:
        #compilerstr[0] = cpucompiler + " -fPIC -O3 -c opuApp.cpp";
        if (size(enzyme)>0):   
            compilerstr[0] = cpucompiler + " -D _ENZYME -fPIC -O3 -c opuApp.cpp" + " -Xclang -load -Xclang " + coredir + enzyme;
        else:
            compilerstr[0] = cpucompiler + " -fPIC -O3 -c opuApp.cpp";
        compilerstr[1] = "ar -rvs opuApp.a opuApp.o";        
    else:
        compilerstr[0] = "";
        compilerstr[1] = "";

    if  size(gpucompiler)>0:
        compilerstr[2] = gpucompiler + " -D_FORCE_INLINES -O3 -c --compiler-options '-fPIC' gpuApp.cu";
        compilerstr[3] = "ar -rvs gpuApp.a gpuApp.o";
    else:
        compilerstr[2] = "";
        compilerstr[3] = "";

    if ( size(cpuflags)>0) and ( size(cpucompiler)>0):
        #str1 = cpucompiler + " -std=c++11 " + maindir + "main.cpp " + "-o serial" + appname + " ";
        str2 = coredir + "commonCore.o " + coredir + "opuCore.o " + "opuApp.a ";
        str3 = cpuflags;
        #compilerstr[4] = str1 + str2 + str3;
        if (size(enzyme)>0):   
            str1 = cpucompiler + " -std=c++11 -D _ENZYME " + maindir + "main.cpp " + "-o serial" + appname + " ";
            compilerstr[4] = str1 + str2 + str3 + " -Xclang -load -Xclang " + coredir + enzyme;
        else:
            str1 = cpucompiler + " -std=c++11 " + maindir + "main.cpp " + "-o serial" + appname + " ";
            compilerstr[4] = str1 + str2 + str3;

    if ( size(cpuflags)>0) and ( size(mpicompiler)>0):
        str1 = mpicompiler + " -std=c++11 -D _MPI " + maindir + "main.cpp " + "-o mpi" + appname + " ";
        str2 = coredir + "commonCore.o " + coredir + "opuCore.o " + "opuApp.a ";
        str3 = cpuflags;
        compilerstr[5] = str1 + str2 + str3;

    if ( size(cpuflags)>0) and ( size(cpucompiler)>0) and ( size(gpucompiler)>0) and ( size(gpuflags)>0):
        str1 = cpucompiler + " -std=c++11 -D _CUDA " + maindir + "main.cpp " + "-o gpu" + appname + " ";
        str2 = coredir + "commonCore.o " + coredir + "gpuCore.o " + coredir + "opuCore.o opuApp.a gpuApp.a ";
        str3 = cpuflags + " " + gpuflags;
        compilerstr[6] = str1 + str2 + str3;

    if ( size(cpuflags)>0) and ( size(mpicompiler)>0) and ( size(gpucompiler)>0) and ( size(gpuflags)>0):
        str1 = mpicompiler + " -std=c++11  -D _MPI -D _CUDA " + maindir + "main.cpp " + "-o gpumpi" + appname + " ";
        str2 = coredir + "commonCore.o " + coredir + "gpuCore.o " + coredir + "opuCore.o opuApp.a gpuApp.a ";
        str3 = cpuflags + " " + gpuflags;
        compilerstr[7] = str1 + str2 + str3;

    if  size(cpucompiler)>0:
        compilerstr[8] = cpucompiler + " -fPIC -O3 -c cpuApp.cpp -fopenmp";
        compilerstr[9] = "ar -rvs cpuApp.a cpuApp.o";
    else:
        compilerstr[8] = "";
        compilerstr[9] = "";

    if ( size(cpuflags)>0) and ( size(cpucompiler)>0):
        str1 = cpucompiler + " -std=c++11 " + maindir + "main.cpp" + "-o openmp" + appname + " ";
        str2 = coredir + "commonCore.o " + coredir + "cpuCore.o cpuApp.a "
        str3 = "-fopenmp " + cpuflags;
        compilerstr[10] = str1 + str2 + str3;

    if ( size(cpuflags)>0) and ( size(mpicompiler)>0):
        str1 = mpicompiler + " -std=c++11 -D _MPI " + maindir + "main.cpp" + "-o openmpmpi" + appname + " ";
        str2 = coredir + "commonCore.o " + coredir + "cpuCore.o cpuApp.a ";
        str3 = "-fopenmp " + cpuflags;
        compilerstr[11] = str1 + str2 + str3;

    for (idx, x) in enumerate(compilerstr):
        print("compilestr[{0}] = {1}".format(idx, x))
    if app['platform'] == "cpu":
        os.system(compilerstr[0]);
        os.system(compilerstr[1]);
        if app['mpiprocs']==1:
            os.system(compilerstr[4]);
        else:
            os.system(compilerstr[5]);
    elif app['platform'] == "gpu":
        os.system(compilerstr[0]);
        os.system(compilerstr[1]);
        os.system(compilerstr[2]);
        os.system(compilerstr[3]);
        if app['mpiprocs']==1:
            os.system(compilerstr[6]);
        else:
            os.system(compilerstr[7]);

    os.chdir("..");

    print("Compiling done!");

    return compilerstr
