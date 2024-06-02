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

Have tow SDK for Naoqi. In this project, we choice python SDK

[Instruction link1](http://doc.aldebaran.com/2-5/dev/python/install_guide.html)</br>
[Instruction link2](https://support.aldebaran.com/support/solutions/articles/80001017327-python-sdk-installation-guide)</br>
[Link fix](https://stackoverflow.com/questions/22403634/installing-python-sdk-for-nao-robots)</br>

Make sure to install Python 2.7 in linux\
Download package `SDKs 2.8.5-Python 2.7 SDK` in [Aldebarab](https://www.aldebaran.com/en/support/nao-6/downloads-softwares/former-versions?os=49&category=76#:~:text=SDKs-,2.8.5,-Python%202.7%20SDK).
Extract package
```
sudo nano ~/.bashrc
```
paste

export PYTHONPATH=${PYTHONPATH}:/path/to/python-sdk/lib/python2.7/site-packages

Ex:
```
export PYTHONPATH=${PYTHONPATH}:/home/huynh/Downloads/python-sdk/lib/python2.7/site-packages
```
replace /path/to/python-sdk with path to folder contain package `SDKs 2.8.5-Python 2.7 SDK`

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
Download Webots `2019a` in [link](https://github.com/cyberbotics/webots/releases?page=2#:~:text=webots_2019a%2Drev1_amd64.deb)

In terminal
```
chmod +x webots_2019a-rev1_amd64.deb
sudo apt install ./webots_2019a-rev1_amd64.deb
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
### 5. Install Choregraphe 2.1.4
#### 5.1. Install the relevant part  
Check version for zlib1g
```
dpkg -s zlib1g
```
install zlib1g 1.2.9 in [link](https://sourceforge.net/projects/libpng/files/zlib/1.2.9/zlib-1.2.9.tar.gz/download)

```
tar -xvf zlib-1.2.9.tar.gz
cd zlib-1.2.9
make
```

```
cd "/home/huynh/Downloads/choregraphe-suite-2.1.4.13-linux64/lib/"
sudo mv libz.so.1 libz.so.1.old

sudo ln -s /lib/x86_64-linux-gnu/libz.so.1 libz.so.1

sudo ln -s /lib/x86_64-linux-gnu/libz.so.1 libz.so.1

/home/huynh/Downloads/choregraphe-suite-2.1.4.13-linux64/bin/choregraphe-bin
```
#### 5.2. Download Choregraphe 2.1.4 in [link](https://community-static.aldebaran.com/resources/2.1.4.13/choregraphe/choregraphe-suite-2.1.4.13-linux64-setup.run)
```
chmod +x choregraphe-suite-2.1.4.13-linux64-setup.run
sudo ./choregraphe-suite-2.1.4.13-linux64-setup.run
```

#### 5.3. Link fix erorr 
>/opt/Softbank Robotics/Choregraphe Suite 2.5/bin/../lib/../lib/../lib/libz.so.1: 
version `ZLIB_1.2.9' not found (required by /usr/lib/x86_64-linux-gnu/libpng16.so.16)

[link](https://nlp.fi.muni.cz/trac/pepper/wiki/InstallationInstructions)

### 6. Install Opencv, numpy for python2.7
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
Download packages `Opencv version 3.4.x.x` and extract

```
```
Install by py of python2.7
```
pip install opencv-python==3.4.1.15
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