# Project

## Development environment
OS Linux-Ubuntu 20.4
python 2.7
choregraphe 2.1.4
SDK naoqi 2.1.4
Webots 2019a - version 1

## INSTALL
### 1. Install python 2.7


Install python 2.7 in linux
```
sudo apt update
sudo apt install python2
```
![Check python 2.7](/image_shoots/check_python2.png)

Install pip for python 2.7
```
sudo apt-get install wget
wget https://bootstrap.pypa.io/pip/2.7/get-pip.py
sudo python2.7 get-pip.py
```

### 2. Install Naoqi

Have tow SDKS for Naoqi. In this project, we choice python SDK

[Instruction link1](http://doc.aldebaran.com/2-5/dev/python/install_guide.html)</br>
[Instruction link2](https://support.aldebaran.com/support/solutions/articles/80001017327-python-sdk-installation-guide)</br>
[Link fix](https://stackoverflow.com/questions/22403634/installing-python-sdk-for-nao-robots)</br>

Make sure to install Python 2.7 in linux\
Download package `SDKs 2.8.x-Python 2.7 SDK` in [Aldebarab](https://www.aldebaran.com/en/support/nao-6/downloads-softwares).
Extract package
```
sudo nano ~/.bashrc
```
paste
```
$ export PYTHONPATH=${PYTHONPATH}:/path/to/python-sdk/lib/python2.7/site-packages
```
replace /path/to/python-sdk with path to folder contain package `SDKs 2.1.x-Python 2.7 SDK`

![Install path SDK](/image_shoots/path_python_sdk.png)

To check `naoqi`, run code. If no notification, it cussetfully.
```
python2.7
>>> from naoqi import ALProxy
```
### 3. Install Webost
```
sudo apt-get update
sudo apt-get install ffmpeg libavcodec-extra
sudo apt-get install ubuntu-restricted-extras
```
Download Webots `2019a` in [link](https://github.com/cyberbotics/webots/releases?page=2#:~:text=webots_2018b_amd64.deb)

In terminal
```
chmod +x webots_8.5.0_amd64.deb
sudo apt install ./webots_8.5.0_amd64.deb
```
or install from Snap store
```
sudo snap install webots
```
### 4. Install NaoqiSim

Install libpng and libusb before install naoqisim
```
sudo add-apt-repository ppa:linuxuprising/libpng12
sudo apt update
sudo apt install libpng12-0
sudo apt-get install libusb-0.1-4
```

if you have github, let git clone repositore.
```
git clone https://github.com/cyberbotics/naoqisim.git
```
if you don't have github, download repositori in [here](https://github.com/cyberbotics/naoqisim) then unzip package.

To use `naoqisim` to control robot in `Webots`, need to set environment varibles as follows:
```
export WEBOTS_HOME=/usr/local/webots
```
Install SDK for simulation and control `naoqisim`
```
$ cd ~/naoqisim
$ make
```
Coppy [Makefile](/lib/Makefile) and paste in ../naoqisim-master/controller/naoqisim/Makefile

Build `naoqisim`
```
$ cd controllers/naoqisim
$ make
```

Install opencv for naoqisim

### 5. Install Opencv, numpy for python2.7
Install `Cmake`
```
sudo apt-get install cmake
```
Install `Opencv`
```
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install -y build-essential cmake pkg-config
sudo apt-get install -y libjpeg8-dev libtiff5-dev libjasper-dev libpng12-dev
sudo apt-get install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt-get install -y libxvidcore-dev libx264-dev
sudo apt-get install -y libgtk-3-dev
sudo apt-get install -y libatlas-base-dev gfortran
sudo apt-get install -y python2.7-dev
```
Download packages `Opencv version 3.1.0` and extract

```
wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.1.0.zip
unzip opencv.zip
wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.1.0.zip
unzip opencv_contrib.zip
```
Build lib
```
$ cmake -DCMAKE_BUILD_TYPE=RELEASE -DCMAKE_INSTALL_PREFIX=/usr/local -DENABLE_PRECOMPILED_HEADERS=OFF -DWITH_FFMPEG=OFF ..
$ make
$ sudo make install
```
Then install. Check opencv2 in python
```
import cv2 as cv
print(cv.__version__)
```

Link install opencv for python in linux\
https://gist.github.com/arthurbeggs/06df46af94af7f261513934e56103b30
https://gist.github.com/shinsumicco/52bfcabeccb0290348feee48cd5dcdb9
https://gist.github.com/dongzhuoyao/15e36f4bc9656f3b39f1b7b77c3c8840

### 6. Install Github ( Optional )
Creat account in [Github](https://github.com/)

install packages
```
sudo apt update
sudo apt install git
```
Check installed
```
git --version
```
Login
```
git config --global user.name "your_name"
git config --global user.email "email@example.com"
```

[Intruction and command basic](https://viblo.asia/p/su-dung-git-trong-ubuntu-jaqG0lOPGEKw)


License key:
> 654e-4564-153c-6518-2f44-7562-206e-4c60-5f47-5f45