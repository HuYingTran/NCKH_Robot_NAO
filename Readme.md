# Project
## INSTALL
### 1. Install python 2.7

Install make
```
sudo apt install make
```
Install compiler C (GCC)
```
sudo apt update
sudo apt install build-essential
```
Install python 2.7.5 in linux
```
sudo apt-get install build-essential
sudo apt-get install libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev
cd ~/Downloads/
wget http://python.org/ftp/python/2.7.5/Python-2.7.5.tgz
tar -xvf Python-2.7.5.tgz
cd Python-2.7.5
./configure
make
sudo make altinstall
```
![Check python 2.7](/image_shoots/check_python2.png)

### 2. Install Naoqi

Have tow SDKS for Naoqi. In this project, we choice python SDK

[Instruction link1](http://doc.aldebaran.com/2-5/dev/python/install_guide.html)</br>
[Instruction link2](https://support.aldebaran.com/support/solutions/articles/80001017327-python-sdk-installation-guide)</br>
[Link fix](https://stackoverflow.com/questions/22403634/installing-python-sdk-for-nao-robots)</br>

Make sure to install Python 2.7 in linux\
Download package `SDKs 2.8.x-Python 2.7 SDK` in [Aldebarab](https://www.aldebaran.com/en/support/nao-6/downloads-softwares).
Extract package\
```
$ export PYTHONPATH=${PYTHONPATH}:/path/to/python-sdk/lib/python2.7/site-packages
```
replace /path/to/python-sdk with path to folder contain package `SDKs 2.8.x-Python 2.7 SDK`

![Install path SDK](/image_shoots/path_python_sdk.png)

To check naoqi, run code. If no notification, it cussetfully.
```
python2.7
>>> from naoqi import ALProxy
```
