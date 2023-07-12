# Installation
## 1. Install dependencies
### All platforms
```
pip install -r requirements.txt
```
<!-- ### Linux
System-wide installation
```
sudo apt-get install python3-pyqt5
```
To install inside a virtualenv, assuming PyQt5 is installed globally, run
```
pip install vext.pyqt5
``` -->
### Windows
Download PyQt5 from: https://www.riverbankcomputing.com/software/pyqt/download5

## 2. Install IB API
Download stable version from https://interactivebrokers.github.io/

Upack and navigate to 'pythonclient'. DO NOT USE PIP TO INSTALL! Install using 'setup.py install' instead.

```
python setup.py install
```
## 3. Install CUDA Toolkit
Install an older version of CUDA Toolkit: 11.7-11.9. Version 12.0 and later are not supported. Download [SDK Installer](https://developer.nvidia.com/cuda-downloads) from NVIDIA Developer portal.
