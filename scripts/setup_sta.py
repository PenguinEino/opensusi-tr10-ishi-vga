#!/usr/bin/env python3
"""Build pinned OpenSTA/CUDD locally on Ubuntu 24.04 arm64; no sudo."""
import os
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'.tools'
def run(args,cwd=ROOT,env=None):
    subprocess.run(args,cwd=cwd,env=env,check=True)
for name,url,commit in [
    ('OpenSTA','https://github.com/parallaxsw/OpenSTA.git','396536743ff33852cd8af176988f077219bc8b8d'),
    ('cudd','https://github.com/cuddorg/cudd.git','f54f533303640afd5dbe47a05ebeabb3066f2a25')]:
    p=BASE/name
    if not p.exists():
        run(['git','init',str(p)])
        run(['git','remote','add','origin',url],p)
        run(['git','fetch','--depth','1','origin',commit],p)
        run(['git','checkout','--detach',commit],p)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip()
    if actual!=commit: raise RuntimeError(f'{name}: wrong revision {actual}')
packages=['swig=4.2.0-2ubuntu1','libeigen3-dev=3.4.0-4build0.1','tcl8.6-dev=8.6.14+dfsg-1build1']
(BASE/'debs').mkdir(parents=True,exist_ok=True)
run(['apt-get','download',*packages],BASE/'debs')
for p in (BASE/'debs').glob('*.deb'): run(['dpkg-deb','-x',str(p),str(BASE/'root')])
for f in ['configure.ac','aclocal.m4','configure','config.h.in','Makefile.in']:
    os.utime(BASE/'cudd'/f,None); time.sleep(.05)
run(['./configure','--prefix='+str(BASE/'cudd_install'),'--enable-obj','--enable-static','--disable-shared','--build=aarch64-linux-gnu'],BASE/'cudd')
run(['make','-j4'],BASE/'cudd'); run(['make','install'],BASE/'cudd')
env=dict(os.environ,SWIG_LIB=str(BASE/'root/usr/share/swig4.0'))
run(['cmake','-S',str(BASE/'OpenSTA'),'-B',str(BASE/'OpenSTA/build'),
     '-DCMAKE_BUILD_TYPE=Release','-DCUDD_DIR='+str(BASE/'cudd_install'),
     '-DSWIG_EXECUTABLE='+str(BASE/'root/usr/bin/swig'),
     '-DTCL_INCLUDE_PATH='+str(BASE/'root/usr/include/tcl8.6'),
     '-DTCL_LIBRARY=/usr/lib/aarch64-linux-gnu/libtcl8.6.so.0',
     '-DCMAKE_PREFIX_PATH='+str(BASE/'root/usr'),'-DUSE_TCL_READLINE=OFF'],env=env)
run(['cmake','--build',str(BASE/'OpenSTA/build'),'-j4'],env=env)
(BASE/'bin').mkdir(exist_ok=True)
p=BASE/'bin/sta'
if not p.exists(): p.symlink_to('../OpenSTA/build/sta')
run([str(p),'-version'])
