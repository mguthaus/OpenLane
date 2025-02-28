# OpenLane
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Documentation Status](https://readthedocs.org/projects/openlane/badge/?version=latest)](https://openlane.readthedocs.io/) [![CI](https://github.com/The-OpenROAD-Project/OpenLane/workflows/CI/badge.svg?branch=master)](#) [![Slack Invite](https://img.shields.io/badge/Community-Skywater%20PDK%20Slack-ff69b4?logo=slack)](https://invite.skywater.tools)

OpenLane is an automated RTL to GDSII flow based on several components including OpenROAD, Yosys, Magic, Netgen, Fault, CVC, SPEF-Extractor, CU-GR, Klayout and a number of custom scripts for design exploration and optimization. The flow performs full ASIC implementation steps from RTL all the way down to GDSII.

You can find the latest release of OpenLane [here](https://github.com/The-OpenROAD-Project/OpenLane/releases).

This documentation is also available at [ReadTheDocs](https://openlane.readthedocs.io/).

# Table of contents
- [Prerequisites](#prerequisites)
- [Setting up OpenLane](#setting-up-openlane)
    - [Installation Notes](#installation-notes)
    - [Updating OpenLane](#updating-openlane)
    - [Pulling or Building the OpenLane Docker Container](#pulling-or-building-the-openlane-docker-container)
- [Running OpenLane](#running-openlane)
    - [Command line arguments](#command-line-arguments)
    - [Adding a design](#adding-a-design)
- [OpenLane Architecture](#openlane-architecture)
    - [OpenLane Design Stages](#openlane-design-stages)
    - [OpenLane Output](#openlane-output)
    - [Flow configuration](#flow-configuration)
- [Regression And Design Configurations Exploration](#regression-and-design-configurations-exploration)
- [Hardening Macros](#hardening-macros)
- [Chip Integration](#chip-integration)
- [Commands and Configurations](#commands-and-configurations)
- [How To Contribute](#how-to-contribute)
- [Authors](#authors)
- [Additional Material](#additional-material)
    - [Papers](#papers)
    - [Videos And Tutorials](#videos-and-tutorials)

# Prerequisites
At a minimum:

- Docker 19.03.12+
- GNU Make
- Python 3.6+ with PIP
- Click, Pyyaml: `python3 -m pip install pyyaml click`

## Containerless Install
Please see [here](./docs/source/local_installs.md).

# Setting Up OpenLane
You can start setting up the Sky130 PDK and OpenLane by running:

```bash
    git clone https://github.com/The-OpenROAD-Project/OpenLane.git
    cd OpenLane/
    make pull-openlane
```

---

```bash
    <configuration variables: see notes below>
    make pdk
```
* The default pdk installation directory is $PWD/pdks. If you want to install the PDK at a different location, you'll need add this configuration variable:
    * `export PDK_ROOT=<absolute path to where skywater-pdk and open_pdks will reside>`
        * Be sure to add this to your shell's profile for future use.
* The default SCL to be installed is `sky130_fd_sc_hd`.
    * To change that, you can add this configuration variable: `export STD_CELL_LIBRARY=<Library name, i.e. sky130_fd_sc_ls>`, where the library name is one of:
        - sky130_fd_sc_hd
        - sky130_fd_sc_hs
        - sky130_fd_sc_ms
        - sky130_fd_sc_ls
        - sky130_fd_sc_hdll
    * You can install all Sky130 SCLs by invoking `make full-pdk` instead of `make pdk`.
    * You can install the PDK manually, outside of the Makefile, by following the instructions provided [here][30].
    * Refer to [this][24] for more details on OpenLane-compatible PDK structures.
    
---

```bash
    make test # This a ~5 minute test that verifies that the flow and the pdk were properly installed
```

- The Makefile should do the following when you run the above:
    - Clone Skywater PDK and the specified STD_CELL_LIBRARY, SPECIAL_VOLTAGE_LIBRARY, and IO_LIBRARY and build it.
    - Clone open_pdks and set up the pdk for OpenLane use.
    - Pull the OpenLane Docker image.
    - Test the whole setup with a complete run on a small design, `spm`.

This should produce a clean run for the spm. The final layout will be generated at this path: `./designs/spm/runs/openlane_test/results/magic/spm.gds`.

If everything is okay, you can skip forward to [running OpenLane](#running-openlane).

## Running the Regression Test
To run the regression test, which tests the flow against all available designs under [./designs/](./designs/) vs the the benchmark results, run the following command:

```bash
    make regression_test
```

Your results will be compared with: [sky130_fd_sc_hd](https://github.com/The-OpenROAD-Project/OpenLane/blob/master/regression_results/benchmark_results/SW_HD.csv).

After running you'll find a directory added under [./regression_results/](./regression_results) it will contain all the reports needed for you to know whether you've been successful or not. Check [this](./regression_results/README.md#output) for more details.

**Note**: if `flow_status` is `flow_failed`, that means the design failed. Any reported statistics from any run after the failure of the design is reported as `-1` as well.

## Updating OpenLane

If you already have the repo locally, then no need to re-clone it. You can directly run the following:

```bash
    cd openlane/
    git checkout master
    git pull
    export PDK_ROOT=<absolute path to where skywater-pdk and open_pdks will reside>
    make pull-openlane
    make pdk
    make test # This is to test that the flow and the pdk were properly installed
```

This should install the latest openlane docker container, and re-install the pdk for the latest used version.

## Pulling or Building the OpenLane Docker Container

**DISCLAIMER: This sub-section is to give you an understanding of what happens under the hood in the Makefile. You don't need to run the instructions here, if you already ran `make pull-openlane`.**

For curious users: For more details about the docker container and its process, the [following instructions][1] walk you through the process of using docker containers to build the needed tools then integrate them into OpenLane flow. **You Don't Need To Re-Build It.**


# Running OpenLane
You need to start the Docker container with proper paths mounted. There are two ways to do this.

The easiest way to mount the proper directories into the docker container would be to rely on the Makefile:

```bash
    make mount
```

* **Note:**
    - Default PDK_ROOT is `$(pwd)/pdks`. If you have installed the PDK at a different location, run the following before `make mount`:
        ```bash
        export PDK_ROOT=<absolute path to where skywater-pdk, open_pdks, and sky130A reside>
        ```
    - Default OPENLANE_IMAGE_NAME is dynamically obtained using your current git version. If you want to use a specific image, run the following before `make mount`:
        ```bash
        export OPENLANE_IMAGE_NAME=<docker image name>
        ```

The following is roughly what happens under the hood when you run `make mount` + the required exports:

```bash
    export PDK_ROOT=<absolute path to where skywater-pdk and open_pdks will reside>
    export OPENLANE_IMAGE_NAME=<docker image name>
    docker run -it -v $(pwd):/openlane -v $PDK_ROOT:$PDK_ROOT -e PDK_ROOT=$PDK_ROOT -u $(id -u $USER):$(id -g $USER) $OPENLANE_IMAGE_NAME
```

**Note: this will mount the OpenLane directory and the PDK_ROOT directory inside the container.**

You can use the following example to check the overall setup:

```bash
./flow.tcl -design spm
```

To run OpenLane on multiple designs at the same time, check this [section](#regression-and-design-configurations-exploration).

Having trouble running the flow? check [FAQs](https://github.com/The-OpenROAD-Project/OpenLane/wiki)

## Command line arguments

The following are arguments that can be passed to `flow.tcl`

<table>
    <tr>
        <th width="196">
        Argument
        </th>
        <th >
        Description
        </th>
    </tr>
    <tr>
        <td align="center">
            <code>-design &lt;folder path&gt;</code> <br> (Required)
        </td>
        <td align="justify">
            Specifies the design folder. A design folder should contain a config.tcl defining the design parameters. <br> If the folder is not found, ./designs directory is searched
        </td>
    </tr>
    <tr>
        <td align="center">
            <code>-from &lt;stage&gt;</code> <br> (Optional)
        </td>
        <td align="justify">
            Specifies stage to start flow execution from
        </td>
    </tr>
    <tr>
        <td align="center">
            <code>-to &lt;stage&gt;</code> <br> (Optional)
        </td>
        <td align="justify">
            Specifies stage to stop flow execution at (included)
        </td>
    </tr>
    <tr>
        <td align="center">
            <code>-config_file &lt;file&gt;</code> <br> (Optional)
        </td>
        <td align="justify">
            Specifies the design's configuration file for running the flow. <br> For example, to run the flow using <code>/spm/config2.tcl</code> <br> Use run <code>./flow.tcl -design /spm -config_file /spm/config2.tcl</code> <br> By default <code>config.tcl</code> is used.
        </td>
    </tr>
        <tr>
        <td align="center">
            <code>-config_tag &lt;name&gt;</code> <br> (Optional)
        </td>
        <td align="justify">
            Specifies the design's configuration file for running the flow. <br> For example, to run the flow using <code>designs/spm/config2.tcl</code> <br> Use run <code>./flow.tcl -design spm -config_tag config2</code> <br> By default <code>config</code> is used.
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-tag &lt;name&gt;</code> <br> (Optional)
        </td>
        <td align="justify">
            Specifies a <code>name</code> for a specific run. If the tag is not specified, a timestamp is generated for identification of that run. <br> Can Specify the configuration file name in case of using <code>-init_design_config</code>
        </td>
    </tr>
        <tr>
        </tr>
        <td align="center">
            <code>-run_path &lt;path&gt;</code> <br> (Optional)
        </td>
        <td align="justify">
            Specifies a <code>path</code> to save the run in. By default the run is in <code>design_path/</code>, where the design path is the one passed to <code>-design</code>
        </td>
    </tr>
        <tr>
        </tr>
        <td align="center">
            <code>-save <br> (Optional)
        </td>
        <td align="justify">
            A flag to save a runs results like .mag and .lef in the design's folder
        </td>
    </tr>
        <tr>
        </tr>
        <td align="center">
            <code>-save_path &lt;path&gt;</code> <br> (Optional)
        </td>
        <td align="justify">
            Specifies a different path to save the design's result. This options is to be used with the <code>-save</code> flag
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-src &lt;verilog_source_file&gt; </code> <br> (Optional)
        </td>
        <td td align="justify">
            Sets the verilog source code file(s) in case of using `-init_design_config`. <br> The default is that the source code files are under <code>design_path/src/</code>, where the design path is the one passed to <code>-design</code>
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-init_design_config </code> <br> (Optional)
        </td>
        <td td align="justify">
            Creates a tcl configuration file for a design. <code>-tag &lt;name&gt;</code> can be added to rename the config file to <code>&lt;name&gt;.tcl</code>
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-overwrite</code> <br> (Optional)
        </td>
        <td align="justify">
            Flag to overwirte an existing run with the same tag
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-interactive</code> <br> (Optional)
        </td>
        <td align="justify">
            Flag to run openlane flow in interactive mode
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-file &lt;file_path&gt;</code> <br> (Optional)
        </td>
        <td align="justify">
            Passes a script of interactive commands in interactive mode
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-synth_explore</code> <br> (Boolean)
        </td>
        <td align="justify">
            If enabled, synthesis exploration will be run (only synthesis exploration), which will try out the available synthesis strategies against the input design. The output will be the four possible gate level netlists under &lt;run_path/results/synthesis&gt; and a summary report under reports that compares the 4 outputs.
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-lvs</code> <br> (Boolean)
        </td>
        <td align="justify">
            If enabled, only LVS will be run on the design. in which case the user must also pass: -design DESIGN_DIR -gds DESIGN_GDS -net DESIGN_NETLIST.
        </td>
    </tr>
    <tr>
        </tr>
        <td align="center">
            <code>-drc</code> <br> (Boolean)
        </td>
        <td align="justify">
            If enabled, only DRC will be run on the design. in which case the user must also pass: -design DESIGN_DIR -gds DESIGN_GDS -report OUTPUT_REPORT_PATH -magicrc MAGICRC.
        </td>
    </tr>
</table>


## Adding a design

To add a new design, follow the instructions provided [here](./designs/README.md)

This [file](./designs/README.md) also includes useful information about the design configuration files. It also includes useful utilities for exploring and updating design configurations for each (PDK,STD_CELL_LIBRARY) pair.

# OpenLane Architecture

<table>
  <tr>
    <td  align="center"><img src="./docs/_static/openlane.flow.1.png" ></td>
  </tr>

</table>


## OpenLane Design Stages

OpenLane flow consists of several stages. By default all flow steps are run in sequence. Each stage may consist of multiple sub-stages. OpenLane can also be run interactively as shown [here][25].

1. **Synthesis**
    1. `yosys` - Performs RTL synthesis
    2. `abc` - Performs technology mapping
    3. `OpenSTA` - Performs static timing analysis on the resulting netlist to generate timing reports
2. **Floorplan and PDN**
    1. `init_fp` - Defines the core area for the macro as well as the rows (used for placement) and the tracks (used for routing)
    2. `ioplacer` - Places the macro input and output ports
    3. `pdn` - Generates the power distribution network
    4. `tapcell` - Inserts welltap and decap cells in the floorplan
3. **Placement**
    1. `RePLace` - Performs global placement
    2. `Resizer` - Performs optional optimizations on the design
    3. `OpenDP` - Perfroms detailed placement to legalize the globally placed components
4. **CTS**
    1. `TritonCTS` - Synthesizes the clock distribution network (the clock tree)
5. **Routing**
    1. `FastRoute` - Performs global routing to generate a guide file for the detailed router
    2. `CU-GR` - Another option for performing global routing.
    3. `TritonRoute` - Performs detailed routing
    4. `SPEF-Extractor` - Performs SPEF extraction
6. **GDSII Generation**
    1. `Magic` - Streams out the final GDSII layout file from the routed def
    2. `Klayout` - Streams out the final GDSII layout file from the routed def as a back-up
7. **Checks**
    1. `Magic` - Performs DRC Checks & Antenna Checks
    2. `Klayout` - Performs DRC Checks
    3. `Netgen` - Performs LVS Checks
    4. `CVC` - Performs Circuit Validity Checks

OpenLane integrated several key open source tools over the execution stages:
- RTL Synthesis, Technology Mapping, and Formal Verification : [yosys + abc][4]
- Static Timing Analysis: [OpenSTA][8]
- Floor Planning: [init_fp][5], [ioPlacer][6], [pdn][16] and [tapcell][7]
- Placement: [RePLace][9] (Global), [Resizer][15] and [OpenPhySyn][28] (formerly), and [OpenDP][10] (Detailed)
- Clock Tree Synthesis: [TritonCTS][11]
- Fill Insertion: [OpenDP/filler_placement][10]
- Routing: [FastRoute][12] or [CU-GR][36] (Global) and [TritonRoute][13] (Detailed)
- SPEF Extraction: [SPEF-Extractor][27]
- GDSII Streaming out: [Magic][14] and [Klayout][35]
- DRC Checks: [Magic][14] and [Klayout][35]
- LVS check: [Netgen][22]
- Antenna Checks: [Magic][14]
- Circuit Validity Checker: [CVC][31]

## OpenLane Output

All output run data is placed by default under ./designs/design_name/runs. Each flow cycle will output a timestamp-marked folder containing the following file structure:

```
designs/<design_name>
├── config.tcl
├── runs
│   ├── <tag>
│   │   ├── config.tcl
│   │   ├── logs
│   │   │   ├── cts
│   │   │   ├── cvc
│   │   │   ├── floorplan
│   │   │   ├── klayout
│   │   │   ├── magic
│   │   │   ├── placement
│   │   │   ├── routing
│   │   │   └── synthesis
│   │   ├── reports
│   │   │   ├── cts
│   │   │   ├── cvc
│   │   │   ├── floorplan
│   │   │   ├── klayout
│   │   │   ├── magic
│   │   │   ├── placement
│   │   │   ├── routing
│   │   │   └── synthesis
│   │   ├── results
│   │   │   ├── cts
│   │   │   ├── cvc
│   │   │   ├── floorplan
│   │   │   ├── klayout
│   │   │   ├── magic
│   │   │   ├── placement
│   │   │   ├── routing
│   │   │   └── synthesis
│   │   └── tmp
│   │       ├── cts
│   │       ├── cvc
│   │       ├── floorplan
│   │       ├── klayout
│   │       ├── magic
│   │       ├── placement
│   │       ├── routing
│   │       └── synthesis
```

To delete all generated runs under all designs:
`make clean_runs`
## Flow configuration

1. PDK / technology specific
2. Flow specific
3. Design specific

- A PDK should define at least one standard cell library(SCL) for the PDK. A common configuration file for all SCLs is located in:

    ```
    $PDK_ROOT/$PDK/config.tcl
    ```

    - Sometimes the PDK comes with several standard cell libraries. Each has an own configuration file that defines extra variables specific to the SCL. It may also override variables in the common PDK configuration file which is located in:

        ```
        $PDK_ROOT/$PDK/$STD_CELL_LIBRARY/config.tcl
        ```
    - More on configuring a new PDK in this [section](#setting-up-OpenLane)

- Flow specific variables are related to the flow and are initialized with default values in:

    ```
    ./configuration/
    ```

- Finally, each design should have it's own configuration file with some required variables which are available in this [list][17]. A design configuration file may override any of the variables defined in PDK or flow configuration files. This is the global configurations for the design:

    ```
    ./designs/<design>/config.tcl
    ```
    - More on design configurations in [here](./designs/README.md)

A list of all available variables can be found [here][17].



# Regression And Design Configurations Exploration

As mentioned earlier, everytime a new design or a new (PDK,STD_CELL_LIBRARY) pair is added, or any update happens in the flow tools, a re-configuration for the designs is needed. The reconfiguration is methodical and so an exploration script was developed to aid the designer in reconfiguring his designs if needed.
As explained [here](#adding-a-design) that each design has multiple configuration files for each (PDK,STD_CELL_LIBRARY) pair.

OpenLane provides `run_designs.py`, a script that can do multiple runs in a parallel using different configurations. A run consists of a set of designs and a configuration file that contains the configuration values. It is useful to explore the design implementation using different configurations to figure out the best one(s).

Also, it can be used for testing the flow by running the flow against several designs using their best configurations. For example the following run: spm using its default configuration files `config.tcl.` :
```
python3 run_designs.py --designs spm xtea md5 aes256 --tag test --threads 3
```

For more information on how to run this script, refer to this [file][21]

For more information on design configurations, how to update them, and the need for an exploration for each design, refer to this [file](./designs/README.md)

# Hardening Macros

This is discussed in more detail [here][29].

# Chip Integration

The first step of chip integration is hardening the macros. To learn more about this check this [file][29].

Using OpenLane, you can produce a GDSII from a chip RTL. This is done by applying a certain methodology that we follow using our custom scripts and the integrated tools.

To learn more about Chip Integration. Check this [file][26]

# Commands and Configurations

To get a full list of the OpenLane commands, first introduce yourself to the interactive mode of OpenLane [here][25]. Then check the full documentation of the OpenLane commands [here][34].

The full documentation of OpenLane run configurations could be found [here][2].

# How To Contribute

We discuss the details of how to contribute to OpenLane in [this documentation][32].

# Authors

To check the original author list of OpenLane, check [this][33].

# Additional Material

## Papers
- Ahmed Ghazy and Mohamed Shalan, "OpenLane: The Open-Source Digital ASIC Implementation Flow", Article No.21, Workshop on Open-Source EDA Technology (WOSET), 2020. [Paper](https://github.com/woset-workshop/woset-workshop.github.io/blob/master/PDFs/2020/a21.pdf)
- M. Shalan and T. Edwards, "Building OpenLANE: A 130nm OpenROAD-based Tapeout- Proven Flow : Invited Paper," 2020 IEEE/ACM International Conference On Computer Aided Design (ICCAD), San Diego, CA, USA, 2020, pp. 1-6. [Paper](https://ieeexplore.ieee.org/document/9256623/)
- R. Timothy Edwards, M. Shalan and M. Kassem, "Real Silicon using Open Source EDA," in IEEE Design & Test, doi: 10.1109/MDAT.2021.3050000. [Paper](https://ieeexplore.ieee.org/document/9336682)

## Videos and Tutorials

### OpenLane Specific

- [FOSSi Dial-Up - OpenLane, A Digital ASIC Flow for SkyWater 130nm Open PDK, Mohamed Shalan](https://www.youtube.com/watch?v=Vhyv0eq_mLU)
- [Openlane Overview, Ahmed Ghazy](https://www.youtube.com/watch?v=d0hPdkYg5QI)
- [Free VLSI Tutorial - VSD - A complete guide to install Openlane and Sky130nm PDK](https://www.udemy.com/course/vsd-a-complete-guide-to-install-openlane-and-sky130nm-pdk)
- [Sky130 - Exploring OpenLANE and OpenDB to create a register file , Sylvain Munaut](https://www.youtube.com/watch?v=AT_LcmaCZmw)
- [VLSI SoC EDA openLANE with Skywater 130 PDK, Gary Huang](https://www.youtube.com/watch?v=QnJzoJjC7RQ)

### Caravel & SkyWater PDK
- [Aboard Caravel, Ahmed Ghazy](https://www.youtube.com/watch?v=9QV8SDelURk)
- [FOSSi Dial-Up - Skywater PDK: Fully open source manufacturable PDK for a 130nm process, Tim Ansell](https://www.youtube.com/watch?v=EczW2IWdnOM&)
- [Skywater 130nm PDK - Initial Discovery, Sylvain Munaut](https://www.youtube.com/watch?v=gRYBdTXbxiU)

[1]: ./docker/README.md
[2]: ./configuration/README.md
[4]: https://github.com/YosysHQ/yosys
[5]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/ifp
[6]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/ppl
[7]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/tap
[8]: https://github.com/The-OpenROAD-Project/OpenSTA
[9]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/replace
[10]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/dpl
[11]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/cts
[12]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/grt
[13]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/TritonRoute
[14]: https://github.com/RTimothyEdwards/magic
[15]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/rsz
[16]: https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/pdn
[17]: ./configuration/README.md
[18]: https://github.com/RTimothyEdwards/qflow/blob/master/src/addspacers.c
[19]: https://github.com/The-OpenROAD-Project/
[20]: https://github.com/git-lfs/git-lfs/wiki/Installation
[21]: ./regression_results/README.md
[22]: https://github.com/RTimothyEdwards/netgen
[24]: ./docs/source/PDK_STRUCTURE.md
[25]: ./docs/source/advanced_readme.md
[26]: ./docs/source/chip_integration.md
[27]: https://github.com/HanyMoussa/SPEF_EXTRACTOR
[28]: https://github.com/scale-lab/OpenPhySyn
[29]: ./docs/source/hardening_macros.md
[30]: ./docs/source/Manual_PDK_installation.md
[31]: https://github.com/d-m-bailey/cvc
[32]: ./CONTRIBUTING.md
[33]: ./AUTHORS.md
[34]: ./docs/source/OpenLANE_commands.md
[35]: https://github.com/KLayout/klayout
[36]: https://github.com/cuhk-eda/cu-gr
