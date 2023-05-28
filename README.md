

# Prerequisites

## Install PyQt5
### All platforms
```
pip install PyQt5==5.15.6
pip install PyQtChart==5.15.6
pip install PyQtWebEngine==5.15.6
pip install plotly==5.14.1
pip install pandas
pip install dash==2.9.3
pip unstall requests
```
### Linux
System-wide installation
```
sudo apt-get install python3-pyqt5
```
To install inside a virtualenv, assuming PyQt5 is installed globally, run
```
pip install vext.pyqt5
```
### Windows, Mac
Download PyQt5 from: https://www.riverbankcomputing.com/software/pyqt/download5

## Install IB API
Download stable version from https://interactivebrokers.github.io/

Upack and navigate to 'pythonclient'. Don't use pip to install! Run 'setup.py install' instead.

```
python setup.py install
```
