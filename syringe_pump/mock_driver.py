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
from logging import debug,info,warning,error
import sys
from pdb import pm

from numpy import nan, inf

from driver import Driver

#following example in https://stackoverflow.com/questions/2291772/virtual-serial-device-in-python
import os, pty, serial
master, slave = pty.openpty()
s_name = os.ttyname(slave)

class Device():
    def __init__(self):
        self.position = 0.0
        self.cmd_position = 0.0
        self.speed = 0.001
        self.valve = b'i'
        self.running = False
        self.time_step = 0.1
        self.busy = False


    def run_once(self):
        if self.position != self.cmd_position:
            self.busy = True
            sign = (self.cmd_position - self.position)/abs(self.cmd_position - self.position)
            step = sign*self.speed*self.time_step
            sleep(self.time_step)
            if abs(self.position - self.cmd_position) <= step:
                self.position = self.cmd_position
            else:
                self.position += sign*self.speed*self.time_step
            sleep(self.time_step)
        else:
            self.busy = False

    def run(self):
        while self.running:
            self.run_once()

    def start(self):
        from ubcs_auxiliary.threading import new_thread
        self.running = True
        new_thread(self.run)

    def write(self):
        """
        write reply command to a serial port
        """


class Driver(Driver):

    def discover(self):
        from serial import Serial
        port = Serial(s_name)
        return port

    @property
    def available_ports(self):
        return [s_name]

    def write(self,command, port = None):
        """
        serial write command. the port attribute is optional. if port left None, the self.port object will be used. this fucnction is both Python 2 and 3 compatible.

        Parameters
        ----------
        command: strin
            string command to be written into serial input buffer
        port: object
            serial port object

        Returns
        -------

        Examples
        --------
        >>> driver.write()
        """
        #command = bytes(command,encoding='Latin-1')
        if type(command) is not bytes:
            warning('Depreciation warning: expecting type bytes in write but received %r' % command)
            command = command.encode('Latin-1')
        debug('encoding: {}'.format(command))
        if port is None:
            port = self.port
        if port is not None:
            port.flushInput()
            debug('write(): pid %r and command = %r' %(self.pump_id,command))
            sleep(dict[command]['delay'])
            command = dict[command]['reply']
            port.write(command)
            self.last_command = command
        else:
            error('Port is not specified')

    def read(self, port = None):
        """
        serial read command. the port attribute is optional. if port left None, the self.port object will be used. this fucnction is both Python 2 and 3 compatible.

        Parameters
        ----------
        port: object
            serial port object

        Returns
        -------
        reply: string
            returns string from serial buffer

        Examples
        --------
        >>> driver.read()
        "ÿ/0`0\\x03\\r\\n"
        """
        from sys import version_info
        if port is None:
            port = self.port
        if port is not None:
            reply = os.read(master,1000)
            self.last_reply = reply
        else:
            reply = ''
        debug("read: {}".format(reply))
        return reply

driver = Driver()
dict = {}
#initialization commands
dict[b"/1"+b'Y7,0,0'+b"R\r"] = {'reply':bytearray("ÿ/0@\x03\r\n".encode()),'delay':0}
dict[b"/1"+b'Z7,0,0'+b"R\r"] = {'reply':bytearray('ÿ/0@\x03\r\n'.encode()),'delay':0}

#Busy query
dict[b"/1?29R\r"] = {}
dict[b"/1?29R\r"]['reply'] = bytearray('ÿ/0`0\x03\r\n'.encode())
dict[b"/1?29R\r"]['delay'] = 0
dict[b"/1?29R\r"]['description'] = b'busy'

#get position
dict[b'/1?18\r'] = {}
dict[b'/1?18\r']['reply'] = bytearray(b"\xff/0`0.000\x03\r\n") #
dict[b'/1?18\r']['delay'] = 0
dict[b'/1?18\r']['description'] = 'position'

#Get Valve
dict[b'/1?20R\r' ] = {}
dict[b'/1?20R\r']['reply'] = b'\xff/0`o\x03\r\n'
dict[b'/1?20R\r']['delay'] = 0.1 #
dict[b'/1?20R\r']['description'] = 'get valve'

#get ID number
dict[b'/1?80\r' ] = {}
dict[b'/1?80\r']['reply'] = b'\xff/0`ZA1\x03\r\n'
dict[b'/1?80\r']['delay'] = 0.1 #
dict[b'/1?80\r']['description'] = 'get id number'

#Set Valve

driver = Driver()

if __name__ == "__main__":
    from tempfile import gettempdir

    import logging;
    logging.basicConfig(filename=gettempdir()+'/syringe_pump_driver.log',
                                        level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
