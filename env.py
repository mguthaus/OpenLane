#!/usr/bin/env python3

# Copyright 2021 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import io
import os
import sys
import uuid
import shutil
import tempfile
import pathlib
import getpass
import textwrap
import subprocess
from os.path import join, abspath, dirname, exists
from typing import Tuple, Union, List

openlane_dir = dirname(abspath(__file__))
is_root = os.geteuid() == 0
        
# Helper Functions
class chdir(object):
    def __init__(self, path):
        self.path = path
        self.previous = None

    def __enter__(self):
        self.previous = os.getcwd()
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.previous)
        if exc_type is not None:
            raise exc_value

def sh(*args: Tuple[str], root: Union[bool, str] = False, **kwargs):
    """
    args: shell arguments to run
    root:
        if False, the command will be executed as-is
        if True, if the user is not root, "sudo" will be added to the command
        if "retry", the command will be executed as-is first, and if it fails,
            it is retried as root.
    """
    args = list(args)
    if root == True and not is_root:
        args = ["sudo"] + args
    try:
        subprocess.run(args, check=True, stderr=subprocess.PIPE if root == "retry" else None, **kwargs)
    except subprocess.CalledProcessError as e:
        if root == "retry":
            args = ["sudo"] + args
            subprocess.run(args, check=True, **kwargs)
        else:
            raise e

def download(url: str, ext: str) -> str:
    path = f"/tmp/{uuid.uuid4()}.{ext}"
    print(f"{url} -> {path}")
    target = open(path, "wb")
    sh("curl", "-L", url, stdout=target)
    target.close()
    return path

# Installer Class
class Installer(object):
    def __init__(self):
        self.envs: List[Tuple[str, str]] = []

    def input_options(self, env: str, msg: str, options: List[str]) -> str:
        value = None
        env_value = os.getenv(env)
        if env_value is not None and env_value.lower() in options:
            value = env_value
        else:
            options_pretty = [] + options
            options_pretty[0] = f"{options[0].upper()}"
            value = input(f"{msg} [{'/'.join(options_pretty)}] > ")
            if value == "":
                value = options[0]
            while value.lower() not in options:
                value = input(f"Invalid input {value.lower()}, please retry: ")

        value = value.lower()
        self.envs.append((env, value))
        return value

    def input_default(self, env: str, msg: str, default: str) -> str:
        value = None
        env_value = os.getenv(env)
        if env_value is not None:
            value = env_value
        else:
            value = input(f"{msg} [{default}] > ")
            if value == "":
                value = default

        self.envs.append((env, value))
        return value

    def run(self):
        from dependencies.tool import Tool
        from dependencies.get_tag import NoGitException, get_tag
        from dependencies.env_info import OSInfo
        
        try:
            import venv
        except ImportError:
            print("Python venv does not appear to be installed, and is required for local installations.", file=sys.stderr)

        try:
            ol_version = get_tag()
        except NoGitException as e:
            print("Installing OpenLane locally requires a Git repository.", file=sys.stderr)
            exit(-1)

        tools = Tool.from_metadata_yaml(open("./dependencies/tool_metadata.yml").read())
        if self.input_options("RISK_ACKNOWLEDGED", "I affirm that I have read docs/source/local_installs.md and agree to the outlined risks.", ["n", "y"]) != "y":
            return

        print(textwrap.dedent(f"""\
            OpenLane Local Installer ALPHA

                Copyright 2021 Efabless Corporation. Available under the Apache License,
                Version 2.0.

                Ctrl+C at any time to quit.

                Note that this installer does *not* handle:
                - Installing OpenROAD to PATH

                You'll have to do these on your own. We hope that you understand the implications of this.

                This version of OpenLane was tested with this version of OpenRoad:

                    {tools["openroad_app"].version_string}
        """))

        install_dir = self.input_default("INSTALL_DIR", "Where do you want to install Openlane?", "/usr/local/opt/openlane")

        sh("mkdir", "-p", install_dir, root="retry")

        home_perms = os.stat(os.getenv("HOME"))
        sh("chown", "-R", "%i:%i" % (home_perms.st_uid, home_perms.st_gid), install_dir, root="retry")

        os_list = ["other", "ubuntu-20.04", "centos-7", "arch", "macos"]

        # Try to determine user's OS
        set_default_os = lambda x: os_list.insert(0, os_list.pop(os_list.index(x)))

        os_info = OSInfo.get()

        if os_info.distro == "macOS":
            set_default_os("macos")
        
        if os_info.distro == "centos" and os_info.distro_version == "7":
            set_default_os("centos-7")

        if os_info.distro == "ubuntu" and os_info.distro_version == "20.04":
            set_default_os("ubuntu-20.04")

        if os_info.distro in ["manjaro", "arch"]:
            set_default_os("arch")
        
        os_pick = self.input_options("OS", "Which UNIX/Unix-like OS are you using?", os_list)
        
        gcc_bin = os.getenv("CC") or "gcc"
        gxx_bin = os.getenv("CXX") or "g++"
        try:
            if not os_pick in ["centos-7", "macos"]: # The reason we ignore centos 7 and macos is that we're going to just use devtoolset-8/brew gcc anyway.
                all_output = ""
                try:     
                    gcc_ver_output = subprocess.run([gcc_bin, "--version"], stdout=subprocess.PIPE)
                    all_output += gcc_ver_output.stdout.decode("utf8")
                    gx_ver_output = subprocess.run([gxx_bin, "--version"], stdout=subprocess.PIPE)
                    all_output += gx_ver_output.stdout.decode("utf8")
                except:
                    pass
                if "clang" in all_output:
                    print(textwrap.dedent(f"""\
                        We've detected that you're using Clang as your default C or C++ compiler.
                        Unfortunately, Clang is not compatible with some of the tools being
                        installed.

                        You may continue this installation at your own risk, but we recommend
                        installing GCC.

                        You can specify a compiler to use explicitly by invoking this script as
                        follows, for example:

                            CC=/usr/local/bin/gcc-8 CXX=/usr/local/bin/g++-8 python3 {__file__}
                    """))
                    input("Press return if you understand the risk and wish to continue anyways >")
        except FileNotFoundError as e:
            print(e, "(set as either CC or CXX)")
            exit(os.EX_CONFIG)

        install_packages = "no"
        if os_pick != "other":
            install_packages = self.input_options("INSTALL_PACKAGES", "Do you want to install packages for development?", ["no", "yes"])
        if install_packages != "no":
            def cat_all(dir):
                result = ""
                for file in os.listdir(dir):
                    result += open(join(dir, file)).read()
                    result += "\n"
                return result
            if os_pick == "macos":
                brew_packages = cat_all(join(openlane_dir, 'dependencies', 'macos')).strip().split("\n")

                sh("brew", "install", *brew_packages)
            if os_pick == "centos-7":
                yum_packages = cat_all(join(openlane_dir, 'dependencies', 'centos-7')).strip().split("\n") 

                sh("yum", "install", "-y", *yum_packages, root="retry")
            if os_pick == "arch":
                raw = cat_all(join(openlane_dir, 'dependencies', 'arch')).strip().split("\n")

                arch_packages = []
                aur_packages = []

                for entry in raw:
                    if entry.strip() == "":
                        continue

                    if entry.startswith("https://"):
                        aur_packages.append(entry)
                    else:
                        arch_packages.append(entry)


                sh("pacman", "-S", "--noconfirm", "--needed", *arch_packages, root="retry")

                temp_dir = tempfile.gettempdir()
                oaur_path = os.path.join(temp_dir, "openlane_aur")
                pathlib.Path(oaur_path).mkdir(parents=True, exist_ok=True)
                with chdir(oaur_path):
                    for package in aur_packages:
                        sh("rm", "-rf", "current")
                        sh("git", "clone", package, "current")
                        with chdir("current"):
                            sh("makepkg", "-si")
            if os_pick == "ubuntu-20.04":
                raw = cat_all(join(openlane_dir, 'dependencies', 'ubuntu-20.04')).strip().split("\n")

                apt_packages = []
                apt_debs = []

                for entry in raw:
                    if entry.strip() == "":
                        continue
                    
                    if entry.startswith("https://"):
                        apt_debs.append(entry)
                    else:
                        apt_packages.append(entry)
                sh("apt-get", "update", root="retry")
                sh("apt-get", "install", "-y", "curl", root="retry")
                for deb in apt_debs:
                    path = download(deb, "deb")
                    sh("apt-get", "install", "-y", "-f", path, root="retry")
                sh("apt-get", "install", "-y", *apt_packages, root="retry")

        print("To re-run with the same options: ")
        print(f"{' '.join(['%s=%s' % env for env in self.envs])} python3 {__file__}")
        
        run_env = os.environ.copy()
        run_env["PREFIX"] = install_dir

        path_elements = ["$PATH", "$OL_DIR/bin"]

        if os_pick == "centos-7":
            run_env["CC"] = "/opt/rh/devtoolset-8/root/usr/bin/gcc"
            run_env["CXX"] = "/opt/rh/devtoolset-8/root/usr/bin/g++"
            run_env["PATH"] = f"/opt/rh/devtoolset-8/root/usr/bin:{os.getenv('PATH')}"
            run_env["LD_LIBRARY_PATH"] = f"/opt/rh/devtoolset-8/root/usr/lib64:/opt/rh/devtoolset-8/root/usr/lib:/opt/rh/devtoolset-8/root/usr/lib64/dyninst:/opt/rh/devtoolset-8/root/usr/lib/dyninst:/opt/rh/devtoolset-8/root/usr/lib64:/opt/rh/devtoolset-8/root/usr/lib:{os.getenv('LD_LIBRARY_PATH')}"
            run_env["CMAKE_INCLUDE_PATH"] = f"/usr/include/boost169:{os.getenv('CMAKE_INCLUDE_PATH')}"
            run_env["CMAKE_LIBRARY_PATH"] = f"/lib64/boost169:{os.getenv('CMAKE_LIBRARY_PATH')}"
        elif os_pick == "macos":
            def get_prefix(tool):
                return subprocess.check_output([
                    "brew", "--prefix", tool
                ]).decode('utf8').strip()

            klayout_app_path = self.input_default("KLAYOUT_MAC_APP", "Please input the path to klayout.app (0.27.3 or later): ", "/Applications/klayout.app")
            klayout_path_element = join(klayout_app_path, "Contents", "MacOS")

            run_env["CC"] = f"{get_prefix('gcc')}/bin/gcc-11"
            run_env["CXX"] = f"{get_prefix('gcc')}/bin/g++-11"
            run_env["PATH"] = f"{get_prefix('swig@3')}/bin:{get_prefix('bison')}/bin:{get_prefix('flex')}/bin:{get_prefix('gnu-which')}/bin:{os.getenv('PATH')}"
            run_env["MAGIC_CONFIG_OPTS"] = f"--with-tcl={get_prefix('tcl-tk')} --with-tk={get_prefix('tcl-tk')}"
            run_env["READLINE_CXXFLAGS"] = f"CXXFLAGS=-L{get_prefix('readline')}/lib"

            path_elements.append(f"{klayout_path_element}")
            path_elements.append(f"{get_prefix('gnu-sed')}/libexec/gnubin")
            path_elements.append(f"{get_prefix('bash')}/bin")
        else:
            run_env["CC"] = gcc_bin
            self.envs.append(("CC", gcc_bin))
            run_env["CXX"] = gxx_bin
            self.envs.append(("CXX", gxx_bin))

        def copy(f):
            sh("rm", "-rf", f)
            sh("cp", "-r", join(openlane_dir, f), f)

        def install():
            print("Copying files...")
            for folder in ["bin", "lib", "share", "build", "dependencies"]:
                sh("mkdir", "-p", folder)
            copy("configuration")
            copy("scripts")
            copy("flow.tcl")
            copy("dependencies/")

            print("Building Python virtual environment...")
            venv_builder = venv.EnvBuilder(clear=True, with_pip=True)
            venv_builder.create("./venv")
            
            subprocess.run([
                "bash", "-c", f"""
                    source ./venv/bin/activate
                    python3 -m pip install --upgrade -r ./dependencies/python/precompile_time.txt
                    python3 -m pip install --upgrade -r ./dependencies/python/compile_time.txt
                    python3 -m pip install --upgrade -r ./dependencies/python/run_time.txt
                """
            ])

            print("Installing dependencies...")
            with chdir("build"):
                for folder in ["repos", "versions"]:
                    sh("mkdir", "-p", folder)
                    
                skip_tools = re.compile(os.getenv("SKIP_TOOLS") or "Unmatchable")
                for tool in tools.values():
                    if not tool.in_install:
                        continue
                    if skip_tools.match(tool.name) is not None:
                        continue
                    installed_version = ""
                    version_path = f"versions/{tool.name}"
                    try:
                        installed_version = open(version_path).read()
                    except:
                        pass
                    if installed_version == tool.version_string and os.getenv("FORCE_REINSTALL") != "1":
                        print(f"{tool.version_string} already installed, skipping...")
                        continue
                    
                    print(f"Installing {tool.name}...")
                    
                    with chdir("repos"):
                        if not exists(tool.name):
                            sh("git", "clone", tool.repo, tool.name)
                        
                        with chdir(tool.name):
                            sh("git", "fetch")
                            sh("git", "submodule", "update", "--init")
                            sh("git", "checkout", tool.commit)
                            subprocess.run([
                                "bash", "-c", f"""\
                                    set -e
                                    source {install_dir}/venv/bin/activate
                                    {tool.build_script}
                                """
                            ], env=run_env, check=True)

                    with open(version_path, "w") as f:
                        f.write(tool.version_string)

            path_elements.reverse()
            with open("openlane", "w") as f:
                f.write(textwrap.dedent(f"""\
                #!/bin/bash
                OL_DIR="$(dirname "$(test -L "$0" && readlink "$0" || echo "$0")")"

                export PATH={":".join(path_elements)}

                FLOW_TCL=${{FLOW_TCL:-$OL_DIR/flow.tcl}}
                FLOW_TCL=$(realpath $FLOW_TCL)

                source $OL_DIR/venv/bin/activate

                tclsh $FLOW_TCL $@
                """))
            sh("chmod", "+x", "./openlane")

            with open("installed_version", "w") as f:
                f.write(ol_version)
        with chdir(install_dir):
            install()

        print("Done.")
        print(f"To invoke Openlane from now on, invoke {install_dir}/openlane then pass on the same options you would flow.tcl.")

# Commands
def tool_list():
    from dependencies.tool import Tool
    tools = Tool.from_metadata_yaml(open("./dependencies/tool_metadata.yml").read())
    for tool in tools.values():
        print(f"{tool.name}: {tool.version_string}")

def local_install():
    installer = Installer()
    installer.run()

def docker_config():
    from dependencies.env_info import ContainerInfo

    cinfo = ContainerInfo.get()

    if cinfo.engine == "docker":
        if cinfo.rootless:
            print("-u 0", end="")
        else:
            uid = subprocess.check_output([ "id", "-u", getpass.getuser() ]).decode("utf8").strip()
            gid = subprocess.check_output([ "id", "-g", getpass.getuser() ]).decode("utf8").strip()
            print(f"--user {uid}:{gid}", end="")


def issue_survey():
    from dependencies.env_info import OSInfo
    from dependencies.get_tag import get_tag
    
    alerts = open(os.devnull, 'w')

    final_report = ""

    os_info = OSInfo.get()
    final_report += textwrap.dedent(f"""\
        Python: v{os_info.python_version}
        Kernel: {os_info.kernel} v{os_info.kernel_version}
    """)

    if os_info.distro is not None:
        final_report += textwrap.dedent(f"""\
            Distribution: {os_info.distro} {os_info.distro_version or ""}
        """)


    if os_info.container_info is not None:
        final_report += textwrap.dedent(f"""\
            Container Engine: {os_info.container_info.engine} v{os_info.container_info.version}
        """)
    else:
        alert = "Critical Alert: No Docker or Docker-compatible container engine was found."
        final_report += f"\n{alert}\n"
        print(alert, file=alerts)

    try:
        final_report += textwrap.dedent(f"""\
            OpenLane Git Version: {get_tag()}
        """)
    except:
        alert = "Critical Alert: OpenLane does not appear to be using a Git repository. This will impair considerable functionality."
        final_report += f"\n{alert}\n"
        print(alert, file=alerts)

    try:
        import click
    except ImportError:
        alert = "Alert: Click is not installed."
        final_report += f"\n{alert}\n"
        print(alert, file=alerts)

    try:
        import venv
    except ImportError:
        alert = "Alert: venv is not installed."
        final_report += f"\n{alert}\n"
        print(alert, file=alerts)

    try:
        import yaml

        from dependencies.verify_versions import verify_versions

        with io.StringIO() as f:
            status = 'OK'
            try:
                mismatches = verify_versions(no_tools=True, report_file=f)
                if mismatches:
                    status = 'MISMATCH'
            except Exception as e:
                status = 'FAILED'
                f.write(f"Failed to compare PDKs.")
                f.write("\n")
            final_report += f"---\nPDK Version Verification Status: {status}\n" + f.getvalue()
        

    except ImportError:
        alert = "Critical Alert: Pyyaml is not installed."
        final_report += f"\n{alert}\n"
        print(alert, file=alerts)

    try:
        git_log = subprocess.check_output(["git", "log", "-n", "3"]).decode("utf8")

        final_report += "---\nGit Log (Last 3 Commits)\n\n" + git_log
    except:
        alert = "Critical Alert: Could not launch git: Are you sure git is installed properly?"
        final_report += f"\n{alert}\n"
        print(alert, file=alerts)

    print(final_report)
    

# Entry Point
def main():
    args = sys.argv[1:]
    commands = {
        "tool-list": tool_list,
        "local-install": local_install,
        "docker-config": docker_config,
        "issue-survey": issue_survey
    }

    if len(args) < 1 or args[0] not in commands.keys():
        print(f"Usage: {sys.argv[0]} ({'|'.join(commands.keys())})", file=sys.stderr)
        sys.exit(os.EX_USAGE)

    commands[args[0]]()

if __name__ == "__main__":
    main()
