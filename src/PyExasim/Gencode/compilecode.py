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
        log.debug(subprocess.check_output(arguments, stderr=subprocess.STDOUT, shell=False, env=os.environ).decode())
    except subprocess.CalledProcessError as e:
        log.debug(e.output.decode())
        raise

def registerHalideGenerators(location, appdir, genexec, generators, genparams, target):
    extrafiles = []
    for (gen, params) in zip(generators, genparams):
        paramsp = ["{0}={1}".format(x,y) for (x,y) in params]
        #
        check_call([location + "/{0}".format(genexec), "-g", gen, "-r", gen, "-o", appdir, "target={0}-no_bounds_query".format(target)] + paramsp)
        extrafiles.append("{0}.a".format(gen))
    return extrafiles
        
    
def compilefiles(compiler, target, srcfile, link=False, dflags=[],srcobjects=[], flags=[], ocompilerflags=[]):
    args = [compiler] + dflags
    if link:
        args += [srcfile]
    else:
        if ocompilerflags != []:
            qouted = ["'{0}'".format(x) for x in ocompilerflags]
            extraflags = ["--compiler-options"] + qouted
        else:
            extraflags = []
        args += ["-c"] + extraflags + [srcfile]
    args += ["-o", target] + srcobjects
    args += flags
    check_call(args)

def compilecode1(app):
    srcdir = app["srcdir"] + "/"

    osname = app["OS"]
    driverdir = srcdir + "src/Kernel/AppDriver/"
    libdir = srcdir + "lib/" + osname + "/"
    maindir = srcdir + "src/Kernel/Main/"
    mainfile = maindir + "main.cpp"
    applicationdir = app["appdir"] + "/"
    arch = app["platform"]
    log.info("Compiling Code in {0}".format(applicationdir))
    os.chdir(applicationdir)
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
    havehalide = app["halide"] != ""


    log.info("Copying needed files from src dir ({0})".format(srcdir))
    
    shutil.copyfile(driverdir  + "opuApp.cpp", applicationdir + "opuApp.cpp")
    shutil.copyfile(driverdir  + "cpuApp.cpp", applicationdir + "cpuApp.cpp")
    if arch == "gpu":
        shutil.copyfile(driverdir  + "gpuApp.cu", applicationdir + "gpuApp.cu")

    log.info("Copying object files from lib dir ({0})".format(libdir))
    shutil.copyfile(libdir + "commonCore.o", applicationdir + "commonCore.o")
    shutil.copyfile(libdir + "opuCore.o", applicationdir + "opuCore.o")
    if arch == "gpu":
        shutil.copyfile(libdir + "gpuCore.o", applicationdir + "gpuCore.o")
    
    log.info("Compiling opuApp.cpp")
    compilefiles(cpucompiler, "opuApp.o", "opuApp.cpp", flags=cpuflags)
    if arch == "cpu":
        log.info("Compiling for CPU")
        if mpiprocs == 1:
            if havehalide:
                numdofs = app["dofs"]
                extrafiles = registerHalideGenerators(app["srcdir"] + "/src/Kernel/HalideBlas", applicationdir, "cgsparts", ["dgemvnormed", "dgemtv"], [[("dofs", numdofs)], [("dofs", numdofs)]], "host")
                halideIncludes = app["halide"] + "/include/"
                halideObjects = app["halide"] + "/src/"
                compilefiles(cpucompiler, "serial" + appname, mainfile, link=True, flags=cpuflags + ["-lpthread", "-L", halideObjects, "-I", halideIncludes, "-I", applicationdir], srcobjects=["commonCore.o", "opuCore.o", "opuApp.o"] + extrafiles, dflags=["-D _HALIDE", "-D _GLIBCXX_USE_CXX11_ABI=0"])
            else:
                compilefiles(cpucompiler, "serial" + appname, mainfile, link=True, flags=cpuflags, srcobjects=["commonCore.o", "opuCore.o", "opuApp.o"])
        else:
            log.info("Compiling for MPI-CPU")
            compilefiles(mpicompiler, "mpi" + appname, mainfile, link=True, dflags=["-D _MPI"], flags=cpuflags,srcobjects=["commonCore.o", "opuCore.o", "opuApp.o"])

    elif arch == "gpu":
        log.info("Compiling for GPU")
        compilefiles(gpucompiler, "gpuApp.o", "gpuApp.cu", dflags=["-D_FORCE_INLINES"], flags=gpuflags, ocompilerflags=cpuflags)
        if mpiprocs == 1:
            copmilefiles(cpucompiler, "gpu" + appname, mainfile, link=True, dflags=["-D _CUDA"], flags=cpuflags + gpuflags, srcobjects=["opuCore.o", "opuApp.o", "gpuApp.o", "commonCore.o", "gpuCore.o"])
        else:
            log.info("Compiling for MPI-GPU")
            copmilefiles(mpicompiler, "gpumpi" + appname, mainfile, link=True, dflags=["-D _MPI", "-D _CUDA"], flags=cpuflags + gpuflags, srcobjects=["opuCore.o", "opuApp.o", "gpuApp.o", "commonCore.o", "gpuCore.o"])
    else:
        log.error("Unrecgonized architecture")
        raise Exception("UA")
    os.chdir("..")


def compilecode(app):
    raise Exception("Bad compile version")
