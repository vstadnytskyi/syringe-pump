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
__version__ = '0.1'
import sys
#if sys.version_info[0] < 3:
#    raise Exception("Must be using Python 3")
#    str.encode(my_str)
#else:

from time import sleep,time
from logging import debug,info,warn,error
import sys
from pdb import pm

from numpy import nan, inf

class Driver(object):

    def __init__(self):
        self.orientation = ''
        self.serial_communication_dt = 0.1 #minimum distance between two serial commands.
        self.pump_id = None
        self.port = None
        #self.speed = 25
        #self.cmd_position = 0
        #self.position = nan

#  ############################################################################
#  RS-232 Communication Commands
#  ############################################################################

    def discover(self):
        """Find the serial ports for each pump controller"""
        from serial import Serial
        from threading import RLock as Lock
        from sys import version_info
        self.lock = Lock()
        available_ports = self.available_ports
        for port_name in self.available_ports:
            try:
                debug("Trying self.port %s..." % port_name)
                port = Serial(port_name)
            except:
                available_ports.pop(available_ports.index(port_name))
        debug("available ports {}...".format(available_ports))
        for port_name in available_ports:
            debug("Trying self.port %s..." % port_name)
            port = Serial(port_name)
            port.baudrate = 9600
            port.timeout = 2
            port.flushInput()
            port.flushOutput()
            port.write("/1?80\r")
            full_reply = port.readline()
            if len(full_reply) != 0:
                debug("port %r: full_reply %r" % (port_name,full_reply))
                reply = full_reply[3:][:-3]
                status = reply[0]
                pump_id = reply[3]
                debug("self.ports %r: full_reply %r, status %r, pump_id %r" % (port_name,full_reply, status, pump_id))
            else:
                pump_id = 0
                debug("port %r: full_reply %r" % (port_name,full_reply))
            #except Exception as msg:
            #    pump_id = 0
            #    debug("%s: %s" % (Exception,msg))

            if self.pump_id == int(pump_id): # get pump id for new_pump
                self.port = port
                info("self.port %r: found pump %r" % (port_name,self.pump_id))
                break
            else:
                port.close()
                debug("closing the serial connection")


    @property
    def available_ports(self):
        """return the list of comport devices"""
        from platform import system
        from serial.tools.list_ports import comports
        if system() == 'Darwin':
            prefix = 'cu.usbserial'
        elif system() == 'Windows':
            prefix = 'COM'
        elif system() == 'Linux':
            prefix = '/dev/ttyUSB'
        else:
            prefix = ''
        return [port.device for port in comports() if prefix in port.device]


    def write(self,command, port = None):
        """
        serial write command
        input: command, port
        """
        import sys
        if sys.version_info[0] == 3:
            command = command.encode('Latin-1')
        if port is None:
            port = self.port
        if port is not None:
            port.flushInput()
            debug('write(): pid %r and command = %r' %(self.pump_id,command))
            port.write(command)
        else:
            error('Port is not specified')

    def read(self, port = None):
        """

        """
        from sys import version_info
        if port is None:
            port = self.port
        if port is not None:
            reply = port.readline()
            self.last_reply = reply
        else:
            reply = ''

        if version_info[0] == 3:
            return reply.decode("Latin-1")
        else:
            return reply

    def query(self,command, port = None):
        """
        write-read command with build in threading lock to insure no commands can be send within 100 ms
        """
        from time import time
        from sys import version_info
        timeout = self.serial_communication_dt
        debug('query(): pid {!r} and command = {!r}'.format(self.pump_id,command))
        if port is None:
            port = self.port
        if port is not None:
            t1 = time()
            with self.lock:
                self.last_command = command
                port.flushInput()
                port.flushOutput()
                if version_info[0] == 3:
                    self.write(command = command.encode('Latin-1'), port = port)
                else:
                    self.write(command = command, port = port)
                reply = self.read(port = port)
            dt = self.serial_communication_dt - (time()-t1)
            debug('query: left of dt = {:.3f}. will sleep this amount'.format(dt))
            if dt > 0:
                if dt < 0 : dt = 0
                sleep(dt)
        else:
            reply = None
        #parsing reply
        if reply is not None and reply is not '':
            #the positinonal reply \xff/0`0.000\x03\r\n is sandwiched between '\x03\r\n' and '\xff/0'
            error_code = reply.split('\x03\r\n')[0].split('\xff/0')[1][0]
            value = reply.split('\x03\r\n')[0].split('\xff/0')[1][1:]
            dict = self.convert_error_code(error_code)
            result = {'value':value,'error_code': error_code, 'busy':dict['busy'],'error':dict['error']}
        else:
            result = {'value':None,'error_code': None, 'busy':None,'error':'no device found'}
        return result

    def waiting(self):
        """
        returns number of byyes in both in and out buffers as tuple

        Parameters
        ----------

        Returns
        -------
        tuple

        Examples
        --------
        >>> ser_port.waiting()
        (0,0)
        """
        reply = (self.port.in_waiting,self.port.out_waiting)
        return reply


    def close(self):
        """
        closes serial port

        Parameters
        ----------

        Returns
        -------

        Examples
        --------
        >>> ser_port.close()
        """
        if self.port is not None:
            self.port.close()


####################################################################################################
### Syringe pumps commands
####################################################################################################
    ### Atomic operations

    def _get_position(self):
        """
        queries position as an atomic command: ""/1?18R\r"

        Parameters
        ----------

        Returns
        -------
        String
            unparse complete respponse string

        Examples
        --------
        >>> ser_port._get_position()
            '\xff/0`0.000\x03\r\n'
        """
        reply = self.query(command = '/1?18\r')
        debug('get_position(): reply = {!r}'.format(reply))
        return reply

    def _set_position(self, position):
        """
        queries set position as an atomic command: "'/1A'+str(pos)+',1R\r'"
        FIXIT - can be this executed if plunger is moving?
        Example:
        "/1A100.000,1R\r" move absolute to 100.0 uL

        Parameters
        ----------
        position: float
            input position as float
        Returns
        -------
        reply: string
            unparse complete response string

        Examples
        --------
        >>> ser_port._set_position()
        """
        pos = round(position,3)
        reply = self.query(command = '/1A'+str(pos)+',1R\r', port = self.port)
        debug('_set_position(): reply = {!r}'.format(reply))
        return reply
    _position = property(_get_position,_set_position)

    def _get_speed(self):
        """
        get speed as an atomic command
        """
        reply = self.query(command = '/1?37\r', port = self.port)
        number = reply['value']
        debug('get_speed(): reply = {}, and number = {}'.format(reply,number))
        return reply
    def _set_speed(self,speed):
        """
        set speed as an atomic command. can be executed if plunger is moving. If plunger is moving accepts speeds below 68.8.

        Example: ''
        "/1V25.0,1F\r" set speed to 25.0 uL/s
        """
        spd = round(speed,3)
        reply = self.query(command = '/1V'+str(spd)+',1R\r')
        return reply
    def _set_speed_on_the_fly(self,speed):
        """
        set speed as an atomic command on the fly. If plunger is moving accepts speeds below 68.8. Speeds above are rejected but no error is issued.

        Example: ''
        "/1V25.0,1F\r" set speed to 25.0 uL/s
        """
        spd = round(speed,3)
        reply = self.query(command = '/1V'+str(spd)+',1F\r')
        return reply
    _speed = property(_get_speed,_set_speed)

    def get_speed(self):
        reply = self._get_speed()
        return reply
    def set_speed(self,speed):
        """
        set speed as an atomic command. can be executed if plunger is moving. If plunger is moving accepts speeds below 68.8.

        Example: ''
        "/1V25.0,1F\r" set speed to 25.0 uL/s
        """
        self.abort()
        spd = round(speed,3)
        reply = self.query(command = '/1V'+str(spd)+',1R\r')
        return reply
    speed = property(get_speed,set_speed)


    ###Set up Commands

    def assign_volume(self, volume = 250):
        """Specifies the syringe volumes for each pump in the dictionary of
        pumps. The command takes effect after power cycling the pumps, and
        need only be executed once.
        accepts 4 different volumes: 50, 100, 250, 500 uL
        # volumes of            ->      result in codes
        50, 100, 250, 500 uL    ->      U93, U94, U90, U95
        """
        volumes = {}
        volumes[50] = 'U93'
        volumes[100] = 'U94'
        volumes[250] = 'U90'
        volumes[500] = 'U95'

        if volume in volumes.keys():
            reply = self.query("/1"+volumes[volume]+"R\r")
        else:
            reply = {'busy': None, 'error': "volume of {} uL is not supported. Choose from {}".format(volume,volumes.keys()), 'error_code': '!', 'value': ''}
        return reply

    def initialize(self, orientation = ''):
        """
        initialization command: Y for left pumps and Z for right pumps
        Z: input on left, output on right
        Rotate valve CW to port 1; move the plunger to zero at speed 7 (default: 2.33 s per 30-mm stroke); rotate valve CW to port 2.
        Y: input on right, output on left
        Rotate valve CCW to Input port 1; move the plunger to zero at speed 7 (default: 2.33 s per 30-mm stroke); rotate valve CCW to Output port 2.

        The initialize command cannot be sent if motor is busy.
        """
        command = ''
        if orientation == '':
            orientation = self.orientation
        if orientation == 'Y':
            command = 'Y7,0,0'
        elif orientation == 'Z':
            command = 'Z7,0,0'
        else:
            reply = ''
        if command != '':
            reply = self.query(command ="/1"+command+"R\r")
        else:
            reply = {'busy': False, 'error': 'Invalid Command, unknown orientation "{}"'.format(orientation), 'error_code': '!', 'value': ''}
        return reply



    def assign_pids(self,pid = None):
        """Assigns pump id to each syringe pump according to dictionary; since
        pump ids are written to non-volatile memory, need only execute once."""
        if pid is not None:
            reply = self.query(command ="/1s0ZA"+str(int(self.pump_id))+"R\r")
        else:
            reply = None
        return reply

    def set_valve_orientation(self, orientation = ''):
        raise NotImplementedError


    def init(self,pump_id, speed = None, backlash = None, orientation = None, volume = None):
        self.pump_id = pump_id
        self.discover()
        #Initializes pump and sets it to correct orientation
        if volume is not None:
            self.assign_volume(volume = volume)
        if backlash is not None:
            self.set_backlash(backlash)
        if speed is not None:
            self.set_speed(speed)
        if orientation is not None:
            self.initialize(orientation = orientation)

    def abort(self):
        """
        Terminates plunger moves [A,P,D] , initialization commands [Z], and delay [M]; does not affect valve moves.
        """
        reply = self.query(command  = '/1TR\r', port = self.port)
        return reply

    def home(self, echo = False):
        """

        FIXIT THIS OPERATION SHOULD BE IN THE DRIVER

        homes syringe pumps.
        The homing parameters are hardcoded:
                speed   orientation     Backlash        start position
        pump1: 25       Y               self.backlash   0
        pump2: 25       Z               self.backlash   0
        pump3: 25       Y               self.backlash   0
        pump4: 25       Z               self.backlash   0

        command = ''
        command += '/1' # start
        command += 'V'+str(speed)+',1' # at speed 'speed' in uL(,1)
        command += 'A'+str(position)+',1' # to position 'position' in uL (,1)
        command += 'R' #execute loaded command symbol
        command += '\r' #cariage return signalling the end of transmission

        """
        if self.pump_id == 1:
            commdn = ''
            command += '/1' # start
            command += 'Y7,0,0' # initialization command for left pumps and Z for right pumps
            command += 'I' # move the valve to position 'i'
            command += 'V25.0,1' # set velocity to 25. V0.100,1
            command += 'K' + str(self.backlash) # set backlash K<n>
            command += 'A0.0,1' #move plunger to absolute position of 0.0 uL
            command += 'R' #Execute loaded Command or Program String
            command += '\r' #
            reply = self.query(command, port = self.port)
        elif self.pump_id == 2:
            reply = self.query("".join(["/1Z7,0,0IV25,1K",str(self.backlash),"A0,1R\r"]), port = self.port)
        elif self.pump_id == 3:
            reply = self.query("".join(["/1Y7,0,0IV25,1K",str(self.backlash),"A0,1R\r"]), port = self.port)
        elif self.pump_id == 4:
            reply = self.query("".join(["/1Z7,0,0IV25,1K",str(self.backlash),"A0,1R\r"]), port = self.port)
        debug('homing of motor %r: reply = %r' %(pump_id,reply))
        self.cmd_position = 0.0
        self.speed = 25.0
        return reply

    def busy(self):
        """
        queries
        """
        reply = self.query(command = '/1?29R\r', port = self.port)
        debug('busy(): reply = %r' %reply)
        return reply

    def get_valve(self):
        reply = self.query(command = '/1?20R\r', port = self.port)
        debug('get_valve(): reply = %r' %reply)
        return reply

    def set_valve(self,value):
        value = value.upper()
        reply = self.query(command = "".join(["/1",str(value),"R\r"]))
        debug('set_valve(value = %r): reply = %r' %(value,reply))
        return reply
    valve = property(get_valve,set_valve)

    def get_backlash(self):
        return self.backlash
    def set_backlash(self,value):
        """
        """
        reply = self.query(command = '/1K'+str(int(value)) + 'R\r', port = self.port)
        debug('set_backlash(): reply = %r' %reply)
        self.backlash = value

    def convert_error_code(self,char = ''):
        """
        the ` is \x60 character or chr(96)
        """
        error_codes = {}
        error_codes[chr(96)] = {'busy':False,'error':'No Error'}
        error_codes['@'] = {'busy':True,'error':'No Error'}
        error_codes['a'] = {'busy':False,'error':'Initialization Error'}
        error_codes['A'] = {'busy':True,'error':'Initialization Error'}
        error_codes['b'] = {'busy':False,'error':'Invalid Command'}
        error_codes['B'] = {'busy':True,'error':'Invalid Command'}
        error_codes['c'] = {'busy':False,'error':'Invalid Operand'}
        error_codes['C'] = {'busy':True,'error':'Invalid Operand'}
        # need to be added FIXIT
        # 7	    g 	G 	Device Not Initialized
        # 8	    h 	H 	Invalid Valve Configuration
        # 9	    i 	I 	Plunger Overload
        # 10	j 	J 	Valve Overload
        # 11	k 	K 	Plunger Move Not Allowed
        # 12	l 	L 	Extended Error Present
        # 13	m 	M 	Nvmem Access Failure
        # 14	n 	N 	Command Buffer Empty or Not Ready
        error_codes['o'] = {'busy':False,'error':'Command Buffer Overflow'}
        error_codes['O'] = {'busy':True,'error':'Command Buffer Overflow'}


        if char in list(error_codes.keys()):
            return error_codes[char]
        else:
            return {'busy':None,'error':None}

    def reset(self):
        """Performs a soft reset on pumps"""
        reply = self.query("/1!R\r", port = self.port)
        debug('reset(): reply = %r' %reply)
        return reply

    #Compund commands

    def move_abs(self,position, speed):
        """Move plunger of pump[pid] to absolute position.
        Plunger moves can be executed in increments or volume
        by appending to the destination ‘,0’ or ‘,1’.
        There are 181,490 increments in a 30-mm stroke.
        The volume in uL is internally calculated from the syringe volume (specified by a U command).
        Two arguments need to be passed: position and speed.
        """
        position = round(position,3)
        command = ''
        command += '/1' # start
        command += 'V'+str(speed)+',1' # at speed 'speed' in uL(,1)
        command += 'A'+str(position)+',1' # to position 'position' in uL (,1) A100.0,1
        command += 'R' #execute loaded command symbol
        command += '\r' #cariage return signalling the end of transmission
        reply = self.query(command = command)
        return reply


    def move_rel(self,position,speed):
        """Move plunger of pump[pid] to relative position."""
        self.abort()
        current = self.position

        if position < 0:
            position = abs(position)
            reply = self.query("".join(["/1J2V",str(speed),",1D",str(position),",1J0R\r"]), port = self.port)
        else:
            reply = self.query("".join(["/1J2V",str(speed),",1P",str(position),",1J0R\r"]), port = self.port)

        return reply

driver = Driver()

if __name__ == "__main__":
    from tempfile import gettempdir

    import logging;
    logging.basicConfig(filename=gettempdir()+'/syringe_pump_driver.log',
                                        level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")

    self = driver # for debugging
    self.pump_id = 1
    #self.discover()

    #functions tested
    # write
    # read
    # query
    # discover

    # initialize
    # _get_position
    # _set_position
    # _get_speed
    # _set_speed
    # _set_speed_on_the_fly
    # assign_volume
    # assign_pids
    # convert_error_code
    # abort
    # move_abs
