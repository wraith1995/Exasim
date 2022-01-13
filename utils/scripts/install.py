#! /usr/bin/env python3
#NOTE: I stole a lot of this from Firedrake to make a strictly inferior, but still good enough build script in under 2 hours.
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
                    filemode=logfile_mode)
# Log to console at INFO level
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)
log = logging.getLogger()
log.info("Running %s" % " ".join(sys.argv))


#Infustructure for running the shell and package manager and pip :
def check_call(arguments):
    try:
        log.debug("Running command '%s'", " ".join(arguments))
        log.debug(subprocess.check_output(arguments, stderr=subprocess.STDOUT, env=os.environ).decode())
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


def git_clone(url):
    name, plain_url, branch = split_requirements_url(url)
    log.info("Cloning %s\n" % name)
    branch = branches.get(name.lower(), branch)
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


def run_pip(args):
    check_call(pip + args)


def run_pip_install(pipargs):
    # Make pip verbose when logging, so we see what the
    # subprocesses wrote out.
    # Particularly important for debugging petsc fails.
    with environment(**blas):
        pipargs = ["-vvv"] + pipargs
        check_call(pipinstall + pipargs)


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
parser.add_argument("--no-package-manager", action='store_false', dest="package_manager",
                        help="Do not attempt to use apt or homebrew to install operating system packages on which we depend.")
#Use llvm
parser.add_argument("--cc", type=file_path,
                        action="store", default=None,
                        help="C compiler to use.. if not, gcc will be used")
parser.add_argument("--cxx", type=file_path,
                        action="store", default=None,
                        help="C++ compiler to use..if not, g++ will be used")
parser.add_argument("--mpicc", type=file_path,
                        action="store", default=None,
                        help="C compiler to use when building with MPI. If not set, MPICH will be downloaded and used.")
parser.add_argument("--mpicxx", type=file_path,
                    action="store", default=None,
                    help="C++ compiler to use when building with MPI. If not set, MPICH will be downloaded and used.")
parser.add_argument("--mpiexec", type=file_path,
                    action="store", default=None,
                    help="MPI launcher. If not set, MPICH will be downloaded and used.")
parser.add_argument("--with-blas-lapack", default=None, type=dir_path,
                    help="Specify path to system BLAS/LAPACK directory. Combined because openblas combines them if manually installed correctly.")

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

#programming languages:
group = parser.add_mutually_exclusive_group()
group.add_argument("--system-python", action="store_true", dest="system_python")
group.add_argument("--with-python", default=None, type=file_path, action="store")

group = parser.add_mutually_exclusive_group()
group.add_argument("--system-julia", action="store_true", dest="system_julia")
group.add_argument("--with-julia", default=None, type=file_path, action="store")

group = parser.add_mutually_exclusive_group()
group.add_argument("--with-matlab", action="store_true", dest="system_matlab")

class InstallError(Exception):
    # Exception for generic install problems.
    pass

def dump_env():
    log.info("Dumping OS Environment:")
    for k in os.environ:
        log.info("Var %s = %s" % (k, os.environ[k]))
    log.info("Dumped OS Enviroment!")

    
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

def check_args(args):
    pass

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
        else:
            log.info("Checking apt")
            try:
                check_call(["apt-get", "--version"])
                check_call(["apt update", "--version"])
            except (subprocess.CalledProcessError, InstallError):
                log.info("Apt-get not found or disabled. Please enable or disable the package manager!")
    else:
        pass

def linux_or_mac(ps, opt1, opt2):
    if osname == "Darwin":
        ps.append(opt1)
    elif osname == "Linux":
        ps.append(opt2)
    else:
        raise InstallError("I don't know how to install on your os.")
def install_packages(args, python, julia, matlab):
    packages = ["autoconf", "automake", "make", "cmake"]
    if args.system_python:
        packages.append("python3")
        packages.append("python3-dev")
        packages.append("pthon3-pip")
    if args.cc is None and args.cxx is None:
        linux_or_mac(packages, "gcc", "build-essential")
    if args.with_blas_lapack is None:
        linux_or_mac(packages, "openblas", "libblas-dev")
        linux_or_mac(packages, "lapack", "liblapack-dev")
    if args.mpicc is None and args.mpicxx is None and args.mpiexec is None:
        linux_or_mac(packages, "mpich", "mpich")

    if args.system_metis:
        linux_or_mac(packages, "libmetis-dev", "metis")
    if args.system_gmsh:
        linux_or_mac(packages, "gmsh", "gmsh")
    if args.system_paraview:
        linux_or_mac(packages, "paraview", "paraview")

    log.info("Installing packages {0}".format(packages))
    for pkg in packages:
        unified_package_manager(pkg)
        
def get_c_cxx(args):
    pass
def get_mpi(args):
    pass
def get_nvcc(args):
    pass
def chec_blas(args):
    pass
def check_cublas(args):
    pass
def extrapackagepaths(args):
    pass
def generate_python(args):
    pass
def generate_julia(args):
    pass
def generate_matlab(args):
    pass
"""
Steps:
-2. Dump enviroment
-1. Use of programming languages
0. If we are using the package manager, check for the PM, install all dependencies that can be installed via package managers
0.1. Install other dependencies that can't be installed this way and are not system packages (e.g. LLVM, Clang, Halide, Tiramisu, Julia, Matlab?)
1. Verify existence of C/CPP compilers
2. Optional existence of MPI+nvcc
3. Verify existence of Blas/laplac
4.. Cublas too?
5. Installation of PL packages required and the associated packages
7. Generation of files with paths
"""
def main():
    args = parser.parse_args()
    dump_env()
    (python, julia, matlab) = check_pl(args)
    check_args()
    check_package_manager()
    install_packages(args, python, julia, matlab)
    #get paths/verify packages
    #install pl packages via package manager
    #install 

    


if __name__ == "__main__":
    main()







