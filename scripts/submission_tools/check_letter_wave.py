#!/usr/bin/env python3
"""Portable recheck of a saved letter-core ngspice transient (raw or gzip)."""
import gzip
import re
from pathlib import Path
import numpy as np


def check(path, case, expected_path):
    path=Path(path)
    raw=gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()
    head,body=raw.split(b'Binary:\n',1);head=head.decode()
    assert 'Flags: real' in head and 'Plotname: Transient Analysis' in head
    count=int(re.search(r'No\. Variables:\s*(\d+)',head)[1])
    points=int(re.search(r'No\. Points:\s*(\d+)',head)[1])
    names={m[2].lower():int(m[1]) for m in re.finditer(r'^\s*(\d+)\s+(\S+)\s+\S+\s*$',head.split('Variables:\n')[1],re.M)}
    data=np.frombuffer(body,dtype=np.float64).reshape(points,count);times=data[:,0]
    assert np.isfinite(data).all() and np.all(np.diff(times)>0)
    sample=(case['delay_ns']+np.arange(case['ticks'])*case['period_ns']+case['sample_offset_ns'])*1e-9
    assert times[-1]>=sample[-1]
    values=np.array([np.interp(sample,times,data[:,names['v('+s.lower()+')']]) for s in case['signals']]).T
    bits=np.where(values<1.5,0,np.where(values>3.5,1,-1))
    first=32 if case['natural'] else 0
    assert not (bits[first:]<0).any(), 'Undefined voltage'
    h=bits[:,6:13]@2**np.arange(7);v=bits[:,13:23]@2**np.arange(10);phase=bits[:,23:30]@2**np.arange(7)
    actual=bits[:,1:6]@np.array([4,2,1,8,16])
    reference=np.array([int(x,16) for x in Path(expected_path).read_text().split()]);assert len(reference)==131072
    prev=tuple(int(x[first-1]) for x in [h,v,phase]) if first else (case['h'],case['v'],case['phase'])
    for i in range(first,case['ticks']):
        ph,pv,pp=prev
        nh,nv=(71,500 if pv==0 else (pv+1)%1024) if ph==100 else ((ph-1)%128,pv)
        np_=(pp+1)%128 if ph==100 and pv==0 else pp
        assert (int(h[i]),int(v[i]),int(phase[i]))==(nh,nv,np_), ('state',i)
        exp=int(reference[(pv<<7)|ph]);x=(71-ph)%128
        if exp&7==4 and pp<64 and 8<=x<72 and (x-8)//16==pp//16:exp|=3
        assert int(actual[i])==exp, ('output',i,int(actual[i]),exp)
        prev=(nh,nv,np_)
    return {'status':'PASS','cycles_checked':case['ticks']-first,'state_bits':24,'output_bits':5}
