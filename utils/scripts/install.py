#! /usr/bin/env python3
#NOTE: I stole a lot of this from Firedrake to make a strictly inferior, but still good enough build script in under 3 hours.
#TODO: Make update use a stored env -- flags beyond install don't really work well here.
import logging
import platform
import subprocess
import sys
import os
import shutil
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import argparse
from collections import OrderedDict
import atexit
import json
import pprint
import shlex
from glob import iglob
from itertools import chain
import re
import importlib
from pkg_resources import parse_version
from pathlib import Path
#Get OS/arch info:
osname = platform.uname().system
arch = platform.uname().machine
#Set logfile:
logfile_directory = os.path.abspath(os.getcwd())
if ("-h" in sys.argv) or ("--help" in sys.argv):
    # Don't log if help displayed to avoid overwriting an existing log
    logfile = os.devnull
else:
    logfile = os.path.join(logfile_directory, 'exasim-install.log')
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-6s %(message)s',
                    filename=logfile,
                    filemode="w")
# Log to console at INFO level
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)
log = logging.getLogger()
log.info("Running %s" % " ".join(sys.argv))

class directory(object):
    """Context manager that executes body in a given directory"""
    def __init__(self, dir):
        self.dir = os.path.abspath(dir)
    def lower(self, n):
        return directory(self.dir + "/" +  n)
    def up(self):
        return directory(self.dir + "/..")
    def __str__(self):
        return str(self.dir)

    def __enter__(self):
        self.olddir = os.path.abspath(os.getcwd())
        log.debug("Old path '%s'" % self.olddir)
        log.debug("Pushing path '%s'" % self.dir)
        os.chdir(self.dir)

    def __exit__(self, *args):
        log.debug("Popping path '%s'" % self.dir)
        os.chdir(self.olddir)
        log.debug("New path '%s'" % self.olddir)
#Infustructure for running the shell and package manager and pip :
def check_call(arguments, shell=False):
    try:
        log.debug("Running command '%s'", " ".join(arguments))
        log.debug(subprocess.check_output(arguments, stderr=subprocess.STDOUT, shell=shell, env=os.environ).decode())
    except subprocess.CalledProcessError as e:
        log.debug(e.output.decode())
        raise


def check_output(args):
    try:
        log.debug("Running command '%s'", " ".join(args))
        return subprocess.check_output(args, stderr=subprocess.STDOUT, env=os.environ).decode()
    except subprocess.CalledProcessError as e:
        log.debug(e.output.decode())
        raise
def brew_install(name, verbose=False):
    arguments = [name]
    if verbose:
        arguments = ["--verbose"] + arguments
    check_call(["brew", "install"] + arguments)


def apt_check(name):
    log.info("Checking for presence of package %s..." % name)
    # Note that subprocess return codes have the opposite logical
    # meanings to those of Python variables.
    try:
        check_call(["dpkg-query", "-s", name])
        log.info("  installed.")
        return True
    except subprocess.CalledProcessError:
        log.info("  missing.")
        return False


def apt_install(names):
    log.info("Installing missing packages: %s." % ", ".join(names))
    if sys.stdin.isatty():
        subprocess.check_call(["sudo", "apt-get", "install"] + names)
    else:
        log.info("Non-interactive stdin detected; installing without prompts")
        subprocess.check_call(["sudo", "apt-get", "-y", "install"] + names)

    
def unified_package_manager(name, verbose=False):
    if osname == "Darwin":
        brew_install(name, verbose=verbose)
    else:
        if not apt_check(name):
            apt_install([name])
        else:
            pass


def split_requirements_url(url):
    name = url.split(".git")[0].split("#")[0].split("/")[-1]
    spliturl = url.split("://")[1].split("#")[0].split("@")
    try:
        plain_url, branch = spliturl
    except ValueError:
        plain_url = spliturl[0]
        branch = "master"
    return name, plain_url, branch


def git_url(plain_url, protocol):
    if protocol == "ssh":
        return "git@%s:%s" % tuple(plain_url.split("/", 1))
    elif protocol == "https":
        return "https://%s" % plain_url
    else:
        raise ValueError("Unknown git protocol: %s" % protocol)


def git_clone(name, plain_url, branch, update=False):
    log.info("Cloning %s\n" % name)
    try:
        check_call(["git", "clone", "-q", "--recursive", git_url(plain_url, "https")])
        log.info("Successfully cloned repository %s." % name)
    except subprocess.CalledProcessError:
        log.error("Failed to clone %s branch %s." % (name, branch))
        raise
    with directory(name):
        try:
            log.info("Checking out branch %s" % branch)
            check_call(["git", "checkout", "-q", branch])
            log.info("Successfully checked out branch %s" % branch)
        except subprocess.CalledProcessError:
            log.error("Failed to check out branch %s" % branch)
            raise
        try:
            log.info("Updating submodules.")
            check_call(["git", "submodule", "update", "--recursive"])
            log.info("Successfully updated submodules.")
        except subprocess.CalledProcessError:
            log.error("Failed to update submodules.")
            raise
    return name
def git_update(name, url=None):
    # Update the named git repo and return true if the current branch actually changed.
    log.info("Updating the git repository for %s" % name)
    with directory(name):
        git_sha = check_output(["git", "rev-parse", "HEAD"])
        # Ensure remotes get updated if and when we move repositories.
        if url:
            _, plain_url, branch = split_requirements_url(url)
            current_url = check_output(["git", "remote", "-v"]).split()[1]
            current_branch = check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()
            protocol = "https" if current_url.startswith("https") else "ssh"
            new_url = git_url(plain_url, protocol)
            # Ensure we only change from bitbucket to github and not the reverse.
            if (new_url != current_url
                and ("bitbucket.org" in current_url)
                and ("github.com/firedrakeproject" in plain_url
                     or "github.com/dolfin-adjoint" in plain_url)):
                log.info("Updating git remote for %s" % name)
                check_call(["git", "remote", "set-url", "origin", new_url])
            # Ensure we only switch loopy branch if loopy is on firedrake and not on a feature branch.
            elif name == "loopy" and current_branch != branch and current_branch == "firedrake":
                log.info("Updating loopy branch to main")
                check_call(["git", "checkout", "-q", branch])

        check_call(["git", "pull", "--recurse-submodules"])
        git_sha_new = check_output(["git", "rev-parse", "HEAD"])
    return git_sha != git_sha_new

def python_pip(python, package):
    check_call([python, "-m", "pip", "install", package])
def julia_pkg(julia, package):
    check_call([julia] + ["-e \" import Pkg; Pkgg.add(\"{0}\") \"".format(package)])

def run_cmd(args):
    check_call(args)



def dir_path(path):
    if path is None:
        return None
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")
def file_path(path):
    if path is None:
        return None
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"readable_file:{path} is not a valid path")
    
parser = ArgumentParser(description="""Install Exasim.""",
                            formatter_class=RawDescriptionHelpFormatter)
parser.add_argument("--no-package-manager", action='store_false', dest="package_manager", default=True,
                        help="Do not attempt to use apt or homebrew to install operating system packages on which we depend; assume they are in the right place")

parser.add_argument("--exasim-directory", action="store", default=os.path.abspath(os.getcwd()), type=dir_path, dest="exasim_directory", help="Location that exasim is already installed in or where you want to install it.")
parser.add_argument("--exasim-branch", action="store", type=str, default="master", help="Branch of Exasim to install")

group = parser.add_mutually_exclusive_group()
group.add_argument("--install", action="store_true", default=False, help="Download Exasim + dependencies, and then configure, and then build.")
group.add_argument("--update", action="store_true", default=False, help="Do not clone exasim; Just rerun install as if clone has just been finished (though we will try to update this clone)")
group.add_argument("--configure", action="store_true", default=False, help="Assume Exasim is installed and all depends are present; just regenerate configuration")
group.add_argument("--build", action="store_true", default=False, help="Assume Exasim is installed and all depends are present and configuration is done; regenerate library files produced by Exasim")

parser.add_argument("--cxxcoreflags", nargs="+", type=str, default=["-fPIC", "-O3","-std=c++17"], help="Arguments for the C++ compiler when compiling core")
parser.add_argument("--gpucoreflags", nargs="+", type=str, default=["-D_FORCE_INLINES","-O3"], help="Arguments for the GPU compiler when compiling core")
parser.add_argument("--gpucxxcoreflags", nargs="+", type=str, default=["-fPIC", "-std=c++17"], help="Arguments for GPU compilers to C++ compiler when compiling core")


parser.add_argument("--cxxflags", nargs="+", type=str, default="-O2 -ldl -lm -lblas -llapack -std=c++17".split(" "), help="Default cxx flags to use")
parser.add_argument("--gpuflags", nargs="+", type=str, default=["-lcudart", "-lcublas"], help="Default nvcc flags to use")
parser.add_argument("--includes", nargs="+", type=directory, default=[], help="Default include directories")
parser.add_argument("--libs", nargs="+", type=directory, default=[], help="Default library directories")
#mpi flags?

parser.add_argument("--cc", type=file_path,
                        action="store", default=None,
                        help="C compiler to use.. if not, gcc will be used")
parser.add_argument("--cxx", type=file_path,
                        action="store", default=None,
                        help="C++ compiler to use..if not, g++ will be used")
parser.add_argument("--mpi", action="store_true", default=False, help="Use MPI.")
parser.add_argument("--mpicc", type=file_path,
                        action="store", default=None,
                        help="C compiler to use when building with MPI. If not set and MPI is enabled, MPICH or openmpi will be downloaded and used.")
parser.add_argument("--mpicxx", type=file_path,
                    action="store", default=None,
                    help="C++ compiler to use when building with MPI. If not set and MPI is enabled, MPICH or openmpi will be downloaded and used.")
parser.add_argument("--mpiexec", type=file_path,
                    action="store", default=None,
                    help="MPI launcher. If not set and MPI is enabled, MPICH or openmpi will be downloaded and used.")
parser.add_argument("--with-blas-lapack", default=None, type=dir_path,
                    help="Specify path to system BLAS/LAPACK directory. Combined because openblas combines them if manually installed correctly.")

#NVCC args
group = parser.add_mutually_exclusive_group()
group.add_argument("--with-nvcc", default=None, type=file_path, action="store", help="NVCC binary. If not set or the system nvcc is not used, GPU will not be enabled.")
group.add_argument("--system-nvcc", default=False, action="store_true", help="Find the NVCC binary in the current PATH.")

##Optional packages: should we install xor should we use a binary you point us to?
group = parser.add_mutually_exclusive_group()
group.add_argument("--system-metis", action="store_true", dest="system_metis")
group.add_argument("--with-metis", default=None, type=file_path, action="store")
group = parser.add_mutually_exclusive_group()
group.add_argument("--system_gmsh", action="store_true", dest="system_gmsh")
group.add_argument("--with-gmsh", default=None, type=file_path, action="store")
group = parser.add_mutually_exclusive_group()
group.add_argument("--system_paraview", action="store_true", dest="system_paraview")
group.add_argument("--with-paraview", default=None, type=file_path, action="store")

parser.add_argument("--cores", action="store", type=int, default=4, help="Number of cores to use when building things.")

group = parser.add_mutually_exclusive_group()
group.add_argument("--build-llvm", default=None, action="store", type=str, help="Build our own LLVM+clang; this requires cmake + ninja build system in your path+LD_LIBRARY_PATH; python3.9, python3.9-dev are also reccomended.")
group.add_argument("--build-llvm-opencilk", default=None, action="store", type=str, help="Build our own LLVM+clang; this requires cmake + ninja build system in your path+LD_LIBRARY_PATH; python3.9, python3.9-dev are also reccomended.")
group.add_argument("--with-llvm", default=None, action="store", type=dir_path, help="LLVM+Clang prefix directory")
group.add_argument("--with-llvm-opencilk", default=None, action="store", type=str, help="Build our own LLVM+clang; this requires cmake + ninja build system in your path+LD_LIBRARY_PATH; python3.9, python3.9-dev are also reccomended.") #NOT IMPLEMENTED

group = parser.add_mutually_exclusive_group()
group.add_argument("--build-cheetah", default=None, action="store_true", dest="build_cheetah", help="Build our own Cheetah on top of our llvm and for use in Halide and other jits.")
group.add_argument("--with-cheetah", default=None, action="store", type=dir_path, help="Path to Cheetah runtime libs compiled for JIT.")

group = parser.add_mutually_exclusive_group()
group.add_argument("--build-halide", default=False, action="store_true", help="Build our own Halide. Requires LLVM")
group.add_argument("--with-halide", default=None, action="store", type=dir_path, help="Path to Halide build path")

#programming languages:
group = parser.add_mutually_exclusive_group()
group.add_argument("--system-python", action="store_true", dest="system_python")
group.add_argument("--with-python", default=None, type=file_path, action="store")

group = parser.add_mutually_exclusive_group()
group.add_argument("--system-julia", action="store_true", dest="system_julia")
group.add_argument("--with-julia", default=None, type=file_path, action="store")

group = parser.add_mutually_exclusive_group()
group.add_argument("--with-matlab", action="store_true", dest="with_matlab")

class InstallError(Exception):
    # Exception for generic install problems.
    pass

def dump_env():
    log.debug("Dumping OS Environment:")
    for k in os.environ:
        if k != "PATH":
            log.debug("Var %s = %s" % (k, os.environ[k]))
        else:
            log.info("Var PATH = %s" % os.environ[k])
    log.debug("Dumped OS Enviroment!")

    
def check_pl(args):
    python = args.system_python or (args.with_python is not None)
    julia = args.system_julia or (args.with_julia is not None)
    matlab = args.with_matlab
    if not (python or julia or matlab):
        raise InstallError("Need at least one PL set via arguments! Try --with-python!")
    if python:
        log.info("Installing Python systems!")
    if julia:
        log.info("Installing Julia systems!")
    if matlab:
        log.info("Installing Matlab systems :(")
    return (python, julia, matlab)

def check_args(arg):
    #if you set the c compiler, you must set the C++ compiler
    if (arg.cc is None ) != (arg.cxx is None):
        raise InstallError("If a c compiler is set, a c++ compiler must be set. And vice-versa.")
    if (arg.mpicc is None) != (arg.mpicxx is None) and (arg.mpiexec is None) != (arg.mpicc is None):
        raise InstallError("If any mpi system is set, they must all be set. And vice-versa.")

    install, update, configure, build = False, False, False, False
    if arg.install:
        install, update, configure, build= True, True, True, True
    if arg.update:
        update, configure, build = True, True, True
    if arg.configure:
        configure, build = True, True
    if arg.build:
        build = True
    if not any([install, update, configure, build]):
        raise InstallError("You must pick one of install, update, confiugure, build")
    else:
        return(install, update, configure, build)

def check_package_manager(args):
    if args.package_manager:
        if osname == "Darwin":
            log.info("Checking homebrew...")
            try:
                check_call("brew", "--version")
            except subprocess.CalledProcessError:
                InstallError("We need homebrew to use the package manager!")
            log.info("Installing command line tools...")
            try:
                check_call(["xcode-select", "--install"])
            except subprocess.CalledProcessError:
                # expected failure if already installed
                pass
        elif osname == "Linux":
            log.info("Checking apt")
            try:
                check_call(["apt-get", "--version"])
                check_call(["apt update", "--version"])
            except (subprocess.CalledProcessError, InstallError):
                log.info("Apt-get not found or disabled. Please enable or disable the package manager!")
        else:
            raise InstallError("I don't know how to install on your os.")
    else:
        log.warning("We are not using the package manager; all required packages must already be in the path or specified manually.")
        pass

def linux_or_mac(ps, opt1, opt2):
    if osname == "Darwin":
        ps.append(opt1)
    elif osname == "Linux":
        ps.append(opt2)
    else:
        raise InstallError("I don't know how to install on your os.")
def install_packages(env, args, python, julia, matlab):
    if not args.package_manager:
        return
    packages = ["autoconf", "automake", "make", "cmake", "ninja-build"]
    if args.system_python:
        packages.append("python3")
        packages.append("python3-dev")
        packages.append("python3-pip")
    if args.cc is None and args.cxx is None:
        linux_or_mac(packages, "gcc", "build-essential")
    if args.with_blas_lapack is None:
        linux_or_mac(packages, "openblas", "libblas-dev")
        linux_or_mac(packages, "lapack", "liblapack-dev")
    if args.mpicc is None and args.mpicxx is None and args.mpiexec is None and args.mpi:
        linux_or_mac(packages, "openmpi", "openmpi")

    if args.system_metis:
        linux_or_mac(packages, "libmetis-dev", "metis")

    if args.system_gmsh:
        linux_or_mac(packages, "gmsh", "gmsh")

    if args.system_paraview:
        linux_or_mac(packages, "paraview", "paraview")


    log.info("Installing packages {0}".format(packages))
    for pkg in packages:
        unified_package_manager(pkg)


def create_exasim_dir(args):
    location = directory(args.exasim_directory)
    if args.install:
        branch = "scheduling"
        exasim_url="github.com/wraith1995/Exasim.git"
        exasim_dir = "Exasim"
        with location:
            git_clone(exasim_dir, exasim_url, branch)
    
    exasim_location = location.lower("Exasim")
    if args.update:
        git_update("Exasim")
    return exasim_location

def find_executable(name, extra_extra_paths="", required=True):
    #TODO: use a list and then join instead of this bs
    extra_paths = extra_extra_paths + ""
    path = extra_paths + os.environ["PATH"]
    try:
        log.info("Trying to find executable {0}".format(name))
        exe = shutil.which(name, path=path)
        if exe is None and required:
            raise InstallError("Failed to find {0}".format(name))
        log.info("Found executable {0} for {1}".format(exe, name))
        return exe
    except Exception as e:
        raise InstallError("Failed to find {0} because of {1}".format(name, e))
def setup_compilers(args, env): #find compilers that are not just set with --cc, --cxx, etc...
    if args.cc is not None or args.build_llvm is not None or args.build_llvm_opencilk is not None:
        pass
    elif args.with_llvm is not None:
        env["cc"] = args.with_llvm + "/bin/clang"
    else:
        env["cc"] = find_executable("gcc")
    if args.cxx is not None or args.build_llvm is not None or args.build_llvm_opencilk is not None:
        pass
    elif args.with_llvm is not None:
        env["cxx"] = args.with_llvm + "/bin/clang++"
    else:
        env["cxx"] = find_executable("g++")
    if args.system_nvcc:
        env["nvcc"] = find_executable("nvcc")
    if args.mpi:
        env["mpicc"] = find_executable("mpicc")
        env["mpicxx"] = find_executable("mpicxx")
        env["mpiexec"] = find_executable("mpiexec")
    else:
        pass
def setup_external_packages(args, env):
    if args.system_metis:
        env["metis"] = find_executable("mpmetis")
    if args.system_gmsh:
        env["gmsh"] = find_executable("gmsh")
    if args.system_paraview:
        env["paraview"] = find_executable("paraview")


#Later, we will add these to make sure things work.
def check_compilers(env):
    pass
def check_external_packages(env):
    pass
def find_languages(env, args, python, julia, matlab):
    if python:
        if args.with_python is not None:
            env["python"] = args.with_python
        else:
            exe = find_executable("python3")
            env["python"] = exe
    if julia:
        if args.with_julia is not None:
            env["jilia"] = args.with_julia
        else:
            exe = find_executable("julia")
            env["julia"] = exe
    if matlab:
        env["matlab"] = args.with_matlab
        
def language_packages(env, python, julia, matlab):
    if python:
        python_packages = ["numpy", "scipy", "sympy"]
        log.info("Checking if pip is installed.")
        check_call([env["python"], "-m", "pip", "--version"])
        log.info("Pip is installed.")
        for p in python_packages:
            log.info("Installing python package %s" % p)
            python_pip(env["python"], p)
            log.info("installed python package %s" % p)
    if julia:
        julia_packaes = ["revise", "Sympy"]
        for p in julia_packaes:
            log.info("Installing julia package %s" % p)
            julia_pkg(env["julia"], p)
            log.info("installed julia package %s" % p)
            
    if matlab:
        log.warning("Install Matlab Symbolic Math Toolkit on your pown")
    

def init_env(args, exasim_dir):
    env = dict()
    env["exasim"] = str(exasim_dir.dir)
    #compilers:
    env["cc"] = args.cc
    env["cxx"] = args.cxx
    env["mpicc"] = args.mpicc
    env["mpicxx"] = args.mpicxx
    env["mpiexec"] = args.mpiexec
    env["nvcc"] = args.with_nvcc

    env["cpuflags"] = args.cxxflags + ["-I{0}".format(f.dir) for f in args.includes] + ["-L{0}".format(f.dir) for f in args.libs]
    env["gpuflags"] = args.gpuflags + ["-I{0}".format(f.dir) for f in args.includes] + ["-L{0}".format(f.dir) for f in args.libs]

    #external:
    env["metis"] = args.with_metis
    env["gmsh"] = args.with_gmsh
    env["paraview"] = args.with_paraview
    env["halidebuild"] = args.with_halide


    #langs:
    env["python"] = None
    env["julia"] = None
    env["matlab"] = None

    #Potentially otheruseful things
    env["PATH"] = []
    env["LD_LIBRARY_PATH"] = []
    env["OS"] = osname
    env["ARCH"] = arch

    #runtimes:
    return env


def gen_constants_file(env, f):
    with open(f, "w") as c:
        for (k,v) in env.items():
            if v is None:
                c.write("{0}=\"\"\n".format(k))
            elif type(v) is list:
                c.write("{0}={1}\n".format(k, v))
            else:
                vv = str(v)
                c.write("{0}=\"{1}\"\n".format(k, vv))

"""
Steps:
0. Parse arguments
1. Dump enviroment
2. Check arguments besides PL
3. Determine choice of programming language
4. Clone exasim
5. Build an env for compilers and other variables we will pass on to exasim
6. Check to see if package managers are around if we want to use them
7. Check the languages we want are present and add them to the env if needed
8. Add packages required by these programming languages
9. Install external dependieces that can't be included via standard means
9.1. LLVM
9.2. Tapiar + Cheetah
9.3. Halide (Rectangular mat-vec generate mode)
9.4. Enzyme Mode
9.5 Tiramisu
9.6 GPU profiling mode
9.7 Debug mode
10. Setup the compiler env and check the compilers
11. Setup the external package env and check them
12. Generate a constants file for use by exasim
13. Generate activation script (put things in the right path (e.g. halide, pythonpath))
"""


def buildllvm(args, env):
    if args.with_llvm is not None:
        with directory(args.with_llvm):
            env["llvm_dir"] = llvmprefix.dir
            env["cc"] = llvmprefix.dir + "/bin/clang"
            env["cxx"] = llvmprefix.dir + "/bin/clang++"
            return llvmprefix
    if args.build_llvm is None and args.build_llvm_opencilk is None:
        return None
    os.mkdir("llvm")
    with directory("llvm"):
        log.info("Cloning LLVM release/12.x")
        llvmbranch = args.build_llvm_opencilk or args.build_llvm
        llvmgit = "https://github.com/llvm/llvm-project.git" if args.build_llvm is not None else "https://github.com/OpenCilk/opencilk-project.git"
        llvmfile = "llvm-project" if args.build_llvm is not None else "opencilk-project"
        run_cmd(["git", "clone", "--depth","1","--branch", "{0}".format(llvmbranch), llvmgit])
        if llvmfile == "opencilk-project":
            with directory(llvmfile):
                log.info("Cloning cilk runtime and cilk tools")
                run_cmd(["git", "clone", "https://github.com/wraith1995/cheetah.git", "-b", "teoc-new-cmake"])
                run_cmd(["git", "clone", "https://github.com/OpenCilk/productivity-tools.git", "cilktools"])
        os.mkdir("build")
        os.mkdir("prefix")
        llvmprefix = directory("prefix")
        with directory("build"):
            log.info("Configuring LLVM.")
            run_cmd(["cmake",
                     "-G", "Ninja",
                     "-S","../{0}/llvm".format(llvmfile),
                     "-DHAVE_LIBEDIT=0",
                     "-DLLVM_ENABLE_RUNTIMES='cheetah;cilktools'", #SWITCH OFF
                     "-DLLVM_ENABLE_TERMINFO=OFF",
                     "-DLLVM_ENABLE_PROJECTS='clang;lld;clang-tools-extra'",
                     "-DLLVM_ENABLE_EH=ON",
                     "-DLLVM_ENABLE_RTTI=ON",
                     "-DLLVM_BUILD_32_BITS=OFF",
                     "-DLLVM_TARGETS_TO_BUILD='X86;ARM;AArch64;Mips;NVPTX;PowerPC'",
                     "-DLLVM_ENABLE_ASSERTIONS=ON",
                     "-DLLVM_ENABLE_PLUGINS=ON",
                     "-DCMAKE_BUILD_TYPE=Release",
                     "-DCMAKE_INSTALL_PREFIX={0}".format(llvmprefix.dir)])
            log.info("Building LLVM.")
            run_cmd(["cmake", "--build", ".", "-j", "{0}".format(args.cores)])
            log.info("Installing llvm")
            run_cmd(["cmake", "--install", "."])
            env["llvm_dir"] = llvmprefix.dir
            env["cc"] = llvmprefix.dir + "/bin/clang"
            env["cxx"] = llvmprefix.dir + "/bin/clang++"
        return llvmprefix
def buildcheetah(args, env, llvmprefix):
    if args.with_cheetah is not None:
        env["LD_LIBRARY_PATH"].append(args.with_cheetah)
        log.info("Updating LD_LIBRARY PATH so that {0} is included".format(args.with_cheetah))
        os.environ["LD_LIBRARY_PATH"] = str(args.with_cheetah.dir) + ":" + os.environ["LD_LIBRARY_PATH"] 
        log.info("LD_LIBRARY_PATH is now: {0}".format(os.environ["LD_LIBRARY_PATH"]))
    elif args.build_cheetah:
        os.mkdir("cheetah")
        with directory("cheetah"):
            log.info("Cloning Cheetah")
            run_cmd(["git", "clone", "https://github.com/wraith1995/cheetah.git", "-b", "teoc-new-cmake"])
            os.mkdir("build")
            os.mkdir("prefix")
            log.info("Configuring cheetah")
            run_cmd(["cmake", "-DCHEETAH_EMULATE_TLS=ON", "-B", "build", "-S", "cheetah", "-DCMAKE_C_COMPILER={0}".format(str(llvmprefix.dir) + "/bin/clang"), "-DLLVM_CONFIG_PATH={0}".format(str(llvmprefix.dir) + "/bin/llvm-config"), "-DCMAKE_INSTALL_PREFIX=prefix"])
            log.info("Buildin cheetah")
            run_cmd(["cmake", "--build", "build/", "-j", str(args.cores)])
            log.info("Installing cheetah")
            run_cmd(["cmake", "--install", "build"])
            cheetahlib = directory("prefix/lib")
            with cheetahlib:
                for f in os.listdir("."):
                    pcheetalib = directory(f)
                    log.info("Updating LD_LIBRARY PATH so that {0} is included".format(str(pcheetalib.dir)))
                    env["LD_LIBRARY_PATH"].append(str(pcheetalib.dir))
                    os.environ["LD_LIBRARY_PATH"] = str(str(pcheetalib.dir)) + ":" + os.environ["LD_LIBRARY_PATH"]
                    log.info("LD_LIBRARY_PATH is now: {0}".format(os.environ["LD_LIBRARY_PATH"]))
    else:
        pass

    
def buildhalide(args, env, llvmprefix):
    if args.with_halide is not None:
        env["halidebuild"] = directory(args.with_halide.dir) #src, include,
        env["halidepybinds"] = directory(args.with_halide.dir + "/python_bindings/src")
        return env["halidebuild"]
    elif not args.build_halide:
        pass
    else:
        os.mkdir("halide")
        with directory("halide"):
            os.mkdir("build")
            log.info("Cloning Halide")
            run_cmd(["git", "clone", "https://github.com/cesmix-mit/Halide.git","-b", "teo-opencilk"])
            log.info("Configuring Halide")
            run_cmd(["cmake",
                     "-G",
                     "Ninja",
                     "-DCMAKE_BUILD_TYPE=Release",
                     "-DLLVM_DIR={0}/lib/cmake/llvm".format(llvmprefix.dir),
                     "-DCLANG_DIR={0}/lib/cmake/clang".format(llvmprefix.dir),
                     "-S",
                     "Halide",
                     "-B",
                     "build"])
            log.info("Building Halide")
            run_cmd(["cmake", "--build", "build", "-j", str(args.cores)])
            halidebuild = directory("build/")
            halidepybinds = directory("build/python_bindings/src")
            env["halidebuild"] = halidebuild.dir
            env["halidepybinds"] = halidepybinds.dir
        return directory("halide/build")
def buildhlaidegenerators(args, env, exasimdir):
    if env["halidebuild"] is not None:
        log.info("Building Halide Generators")
        hb = directory(env["halidebuild"])
        tools = hb.up().lower("Halide/tools")
        halideinclude = hb.lower("include")
        halidebuildsrc = hb.lower("src")
        with exasimdir.lower("src/Kernel/HalideBlas/"):
            generators = ["cgsparts.cpp"]
            for gen in generators:
                log.info("Building generator {0}".format(gen))
                run_cmd([env["cxx"], gen, tools.dir + "/GenGen.cpp", "-g", "-std=c++17", "-fno-rtti", "-I{0}".format(halideinclude.dir), "-L{0}".format(halidebuildsrc.dir), "-lHalide", "-lpthread", "-ldl", "-o", gen[0:-4]])
                
        

def gen_pyactivate(env, exasim_dir):
    with exasim_dir:
        pypath = []
        path = env["PATH"]
        ldpath = env["LD_LIBRARY_PATH"]
        pyexasim = exasim_dir.lower("src/")
        pypath.append(pyexasim)
        if "halidepybinds" in env:
            pypath.append(env["halidepybinds"])
        if "halidebuild" in env:
            ldpath.append(env["halidebuild"])
        with exasim_dir.lower("utils/scripts/"):
            with open("pyactivate.sh", "w") as f:
                s1 = "export PYTHONPATH={0}:$PYTHONPATH\n".format(":".join([str(x) for x in pypath]))
                log.info("Adding " + s1)
                f.write(s1)
                if len(path) != 0:
                    s2 = "export PATH={0}:$PATH\n".format(":".join([str(x) for x in path]))
                    log.info("Adding " + s2)
                    f.write(s2)
                if len(ldpath) != 0:
                    s3 = "export LD_LIBRARY_PATH={0}:$LD_LIBRARY_PATH\n".format(":".join(([str(x) for x in ldpath])))
                    log.info("Adding " + s3)
                    f.write(s3)
                    
    

def main():
    args = parser.parse_args()
    dump_env()
    (install, update, configure, build) = check_args(args)
    (python, julia, matlab) = check_pl(args)
    exasim_dir = create_exasim_dir(args) # uses args to figure install,update
    env = init_env(args, exasim_dir)
    if update:
        check_package_manager(args)
        install_packages(env, args, python, julia, matlab)
    find_languages(env, args, python, julia, matlab)
    if update:
        language_packages(env, python, julia, matlab)
    with exasim_dir:
        if install:
            try:
                os.mkdir("External")
            except FileExistsError:
                pass
            deps = exasim_dir.lower("External")
            with deps:
                llvmprefix = buildllvm(args, env)
                buildcheetah(args, env, llvmprefix)
                buildhalide(args, env, llvmprefix)
                buildhlaidegenerators(args, env, exasim_dir)
                #tiramisu?
                #enzyme
        setup_compilers(args, env) #This is here because in the future we will want to include compiler info from downloaded compilers
        check_compilers(env)
        setup_external_packages(args, env)
        check_external_packages(env)
        if configure:
            if julia:
                with exasim_dir.lower("src/Julia/Preprocessing"):
                    log.info("Generating Julia constants file")
                    gen_constants_file(env, "constants.jl")
            if matlab:
                with exasim_dir.lower("src/Matlab/Preprocessing"):
                    log.info("Generating Matlab constants file")
                    gen_constants_file(env, "constants.m")
            if python:
                with exasim_dir.lower("src/PyExasim/Preprocessing"):
                    log.info("Generating Python constants file")
                    gen_constants_file(env, "constants.py")
        if build:
            with exasim_dir.lower("lib"):
                #Build CPU:
                log.info("Compiling commonCore.cpp")
                check_call([env["cxx"]] + args.cxxcoreflags + ["-c", "commonCore.cpp", "-o", "commonCore.o"])
                log.info("Compiling opuCore.cpp")
                check_call([env["cxx"]] + args.cxxcoreflags + ["-c", "opuCore.cpp", "-o", "opuCore.o"])
                log.info("Making os directory")
                try:
                    os.mkdir(osname)
                except FileExistsError:
                    pass
                osdir = exasim_dir.lower("lib/{0}".format(osname))
                log.info("Copying files to os directory")
                shutil.move("commonCore.o", osname + "/commonCore.o")
                shutil.move("opuCore.o", osname + "/opuCore.o")
                
                
                if env["nvcc"] is not None:
                    log.info("Compiling gpuCore.cu")
                    check_call([env["nvcc"]] + args.gpucoreflags + ["-c", "--compiler-options"] + ["'{0}'".format(f) for f in args.gpucxxcoreflags] + ["gpuCore.cu", "-o", "gpuCore.o"])
                    log.info("Copying gpu files to os directory")
                    shutil.move("gpuCore.o", osname + "/gpuCore.o")                                                        
        if python:
            gen_pyactivate(env, exasim_dir)
            print("Run 'source {0}/utils/scripts/pyactivate.sh' to setup the python modules to setup exasim".format(exasim_dir.dir))
if __name__ == "__main__":
    main()
