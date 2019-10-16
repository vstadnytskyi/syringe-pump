#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Authors: Valentyn Stadnytskyi
Date last modified: 06/19/2019

ASCII communication syntax:
“/“ indicates the start of a command sequence
The first character after the “/“ is the pump address: [1]
n-ASCII characters define the command sequence
“R” executes the command sequence (“F” executes on-the-fly changes)
“CR” or carriage return terminates the command sequence

"""

import sys
from time import sleep,time
from logging import debug,info,warn,error
import sys
from pdb import pm

from numpy import nan, inf

class Driver(object):
    pass
driver = Driver()
command_dict = {}
#initialization commands
d["/1"+'Y7,0,0'+"R\r"] = {'reply':'ÿ/0@\x03\r\n','delay':0}
d["/1"+'Z7,0,0'+"R\r"] = {'reply':'ÿ/0@\x03\r\n','delay':0}
d["/1?29R\r"] = {'reply':'ÿ/0`0\x03\r\n','delay':0,'description':'busy'}
d['/1?18\r' ]['reply'] = '\xff/0`0.000\x03\r\n' #
d['/1?18\r' ]['delay'] = 0
d['/1?18\r' ]['description'] = 'position'

d['/1?20R\r']['reply'] = '\xff/0`o\x03\r\n'
d['/1?20R\r']['delay'] = 0 #
d['/1?20R\r']['description'] = 'get valve'

d['/1?20R\r']['reply'] = '\xff/0`o\x03\r\n'
d['/1?20R\r']['delay'] = 0 #
d['/1?20R\r']['description'] = 'set valve'

'/1IR\r'
command_dict = d
if __name__ == "__main__":
    from tempfile import gettempdir

    import logging;
    logging.basicConfig(filename=gettempdir()+'/syringe_pump_driver.log',
                                        level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
