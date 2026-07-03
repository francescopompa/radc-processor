# RADC Processor

> ⚠️ The software is still in development, please see #current_caveats.

This project provides the necessary software for receiving and processing data captured with the FPGA on the DAQ-board ("board").
For now, it is composed of two python packages:
- `udp_receiver`: Receives data from the board and writes it to disk as binary files.
- `data_parser`: unpacks the stored binary files and stores them as a **pandas DataFrame**. Also provides plot-methods.

It is meant to be used together with radc-processor.
Various tools are also included.

## Dependencies

### Conda environment

To install the conda environment, execute the following commands:
```bash
directory="/kalinka/storage/darkmatter/lngs-neutron-detector/zm6876/software"
mkdir -p $directory/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O $directory/miniconda3/miniconda.sh
bash $directory/miniconda3/miniconda.sh
```
Then, exit and install the environment with:
```bash
conda install -n base conda-libmamba-solver
conda config --set solver libmamba 

conda config --set channel_priority strict 
conda create -n ALMOND python==3.11
```
Then, it's possible to install the Jupyter kernel:
```bash
conda activate ALMOND         
(ALMOND)$ conda install ipykernel
(ALMOND)$ ipython kernel install --user --name=ALMOND
(ALMOND)$ conda deactivate
```

### Python modules
> ⚠️ A virtual environment is not implemented yet (NIY).

Python >= 3.10 is required.
The project itself was developed in Python 3.11.

The required python modules and their version limitations are listed in `requirements.txt`. You can generate the list yourself using
```bash
# pip install pigar
cd radc-processor
pigar generate --with-referenced-comments -c ">=" --dry-run .
```
for example.

### Network and Ports
The requirements from *RADC Commander* apply also here.

## Installation
Once the project has been cloned locally and the dependencies are fulfilled or installed, the package can be installed using:
```bash
cd radc-processor
python -m pip install --upgrade pip # Somehow, this needs to come first
python -m pip install --upgrade setuptools-ext
python -m pip install --upgrade setuptools
python -m pip install -r requirements.txt
python -m pip install -e .
```


To install individual scripts for automatic data taking, preprocessing and backup:
```bash
cd radc-processor
source install_scripts.sh
```
The scripts will be installed in `~/.local/bin` to make it compatible with Kalinka.


## `udp_receiver` / `radc_receiver`

This package receives data sent by the board and writes it to disk.
It uses multiple threads and queues to ensure that no package gets lost.

### Configuration
> ⚠️ For now, configuration is only done via arguments and default values of parameters. **It is imperative that you read the source code to be aware of which parameters you have to provide!** (`udp_receiver/receiver_class.py:20-31`)

### Usage
After installation, the simplest package execution is done with:
```bash
radc_receiver
```
This will start the receiver and show you the usage explanation. It will then wait for commands on the command-line (STDIN).

You can pass non-default parameters in the form of `key=value`-pairs.

(If you want to test the package locally or without installing it first, you can do so with `cd radc-processor` followed by `python -m udp_receiver`.)

#### Available Commands
- `help`: Prints help (usage explanation)
- `start`: starts the receiver using the configured settings.
- `stop`: stops the receiver and closes the file(s) and connection(s).
- `exit`: exits the receiver.
- `catch`: Fetches the "attention" of the board again. Use it in case you do not receive any more data even if the board *should* send some.
- `status`: (todoc)
- `trigger`: (todoc)
- `switch`: (todoc)


## `data_parser`
> ⚠️ W.I.P. --> not ready for production use yet.
> If You want to read the source code first, you can then use it in a live interpreter.

- [ ] Todo: Make color of each event consistent accross different plots (different selections).


## Documentation

Open `documentation.html` for the full code documentation.

Similarly as for the `radc-commander`project, the documentation of this project is automatically generated using `pdoc3`.

> ⚠️ **warning**: After finding out about the problematic behaviour ([64](https://github.com/pdoc3/pdoc/issues/64), [346](https://github.com/pdoc3/pdoc/issues/346), [#397](https://github.com/pdoc3/pdoc/issues/397)) of the maintainer, I am in the process of migrating from `pdoc3` to another alternative. DO NOT INSTALL `pdoc3` IF YOU DON'T WANT TO SUPPORT IT!

The command to update the documentation is currently:
```bash
# cd radc-processor
pdoc --force --html -o docs .
```
(On first creation under Windows do also: `gsudo new-item -ItemType SymbolicLink -Path .\documentation.html -Target .\docs\radc-processor\index.html`)