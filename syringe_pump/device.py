#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Cavro Centris Syringe pump device
author: Valentyn Stadnytskyi
Created: May 28 2019
Last modified: May 28 2019
"""

__version__ = '0.0.0'

from syringe_pump.driver import Driver

import traceback
from pdb import pm



from numpy import nan, mean, std, nanstd, asfarray, asarray, hstack, array, concatenate, delete, round, vstack, hstack, zeros, transpose, split, unique, nonzero, take, savetxt, min, max

from time import time, sleep, clock
import sys
import struct
from pdb import pm
from time import gmtime, strftime, time
from logging import debug,info,warning,error
from struct import pack, unpack
from timeit import Timer, timeit


class Device(object):

    def __init__(self):
        #Thread.__init__(self)
        self.running = False
        #self.daemon = False # OK for main thread to exit even if instance is still running
        self.description = ''

        #circular buffers dictionary contains information about all circular buffers and their type (Server, Client or Queue)
        self.circular_buffers = {}

        self.command_queue = []
        self.position = 0.0
        self.velocity = 0.0
        self.speed = 0.0
        self.flow_speed_high_limit = 5.0
        self.dpos = 0.002

        self.low_level_limit_alarm = 5.0
        self.low_level_limit_warning = 10.0
        self.running = 0
        self.scan_period = 0.001
        self.default_scan_period = 1.0

        self.io_put_queue = None
        self.io_get_queue = None

#  ############################################################################
#  Basic IOC operations
#  ############################################################################
    def first_time_setup(self):
        """default factory setting or first time setup"""
        raise NotImplementedError

    def init(self, pump_id = None, speed = None, backlash = None, orientation = None, volume = None):
        """
        initialize the device level code

        - initializes the driver
        - sets default valve position to 'o'
        - sets initial position to 0.0
        - sets initial speed to input speed value

        Parameters
        ----------
        pump_id: integer
            pump_id
        speed: float
            initial speed of the syringe pump, default is 25
        backlash: float
            the backlash of the syringe pump. The default value is 100
        orientation: string
            the orientation of the syringe pump valve: Y or Z
        volume: float
            the volume of the installed syringe

        Returns
        -------

        Examples
        --------
        >>> device.init(pump_id = 1, speed = 25, backlash = 100,orientation = 'Y', volume = 250)
        """
        from threading import RLock
        self.lock = RLock()

        from circular_buffer_numpy.circular_buffer import CircularBuffer
        self.buffers = {}
        self.buffers['position'] = CircularBuffer(shape = (1*3600*2,2), dtype = 'float64')

        from syringe_pump.driver import Driver
        self.pump_id = pump_id
        self.driver = Driver()
        self.name = 'NIH_syringe_pump_'+ str(pump_id)
        self.prefix = 'NIH:SYRINGE' + str(pump_id)
        if pump_id is not None:
            self.driver.init(pump_id, speed = speed, backlash = backlash, orientation = orientation, volume = volume)
            self.speed = speed
            self.cmd_position = 0.0
            self.valve = 'o'



    def abort(self):
        """
        orderly abort of the current operation

        Parameters
        ----------

        Returns
        -------

        Examples
        --------
        >>> device.abort()
        """
        debug('device.abort')
        reply = self.driver.abort()
        self.process_driver_reply(reply)
        t1 = time()
        flag = True
        while self.get_busy():
            sleep(0.1)
            if time() - t1 > 10.0:
                flag = False
                break


    def close(self):
        """
        orderly close of the serial port and shutdown

        Parameters
        ----------

        Returns
        -------

        Examples
        --------
        >>> device.close()
        """
        self.stop()
        self.abort()
        #self.cleanup()
        self.driver.close()

    def kill(self):
        """
        orderly close of the serial port and shutdown of the device and deletion of the instance

        Parameters
        ----------

        Returns
        -------

        Examples
        --------
        >>> device.kill()
        """
        self.close()
        del self


    def help(self):
        """returns help information in a string format.

    	Parameters
    	----------

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.run_once()

        """
        raise NotImplementedError

    def snapshot(self):
        """returns snapshot of current PVs and their values in a dictionary format

    	Parameters
    	----------

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.run_once()

        """
        raise NotImplementedError

    def start(self):
        """
        starts run() in a separate thread

    	Parameters
    	----------

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.run_once()

        """
        from ubcs_auxiliary.threading import new_thread
        new_thread(self.run)

    def stop(self):
        """
        stop run() in the separate thread

    	Parameters
    	----------

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.run_once()

        """
        self.running = False
        self.iowrite(".RUNNING",value = self.running)


    def run_once(self):
        """
    	run once

    	Parameters
    	----------

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.run_once()

        """
        debug('run_once')
        self.position = self.get_position()
        if not self.busy:
            self.scan_period = self.default_scan_period
        self.iowrite(pv_name = "DMOV",value = self.isdonemoving())
        self.iowrite(pv_name = "RBV",value = self.position)



    def run(self):
        """"""
        self.running = True
        self.iowrite("RUNNING",value = self.running)

        while self.running:
            t = time()
            self.run_once()
            while time() - t < self.scan_period:
                sleep(0.1)

        self.running = False
        self.iowrite("RUNNING",value = self.running)

    def get_busy(self):
        reply = self.driver.busy()
        value = self.process_driver_reply(reply)
        if value is not None:
            return bool(int(self.process_driver_reply(reply)))
        else:
            return None


    def monitor(self,PV_name,value,char_value):
        """Process PV change requests"""
        info("monitor: %s = %r" % (PV_name,value))
        if PV_name == self.prefix + "VAL":
            self.set_cmd_position(value)
        if PV_name == self.prefix + "VELO":
            self.set_speed_on_the_fly(value)
        if PV_name == self.prefix + "VALVE":
            self.set_valve(value)

    def command_monitor(self,PV_name,value,char_value):
        """Process PV change requests"""
        from pickle import loads
        info("command_monitor: %s = %r" % (PV_name,value))
        cmd_dict = {'abort':[],
                    'fill':[],
                    'empty':[],
                    'prime':['N'],
                    'flow':['position','speed']
                    }
        if PV_name == self.prefix+"CMD":
            cmd_in = loads(value)
            try:
                if cmd_in.keys()[0] == 'abort':
                    self.abort()
                if cmd_in.keys()[0] == 'fill':
                    self.fill()
                if cmd_in.keys()[0] == 'empty':
                    self.empty()
                if cmd_in.keys()[0] == 'prime':
                    self.prime(N = cmd_in['prime']['N'])
                if cmd_in.keys()[0] == 'flow':
                    position = cmd_in['flow']['position']
                    speed = cmd_in['flow']['speed']
                    self.flow(position = position, speed = speed)
            except:
                error(traceback.format_exc())

    # input-output(io) controller wrappers

    def iowrite(self, pv_name = None, value = None):
        """
        put dictionary of key:value pairs to IO.

        Parameters
        ----------
        pv_name:  (string)
            string name of the PV
        value:  (string,list,integer,float,array)
            the new value to be submitted to io for processing.

        Returns
        -------

        Examples
        --------
        >>> device.ioput(pv_name = '.running',value = True)

        """
        if self.io_put_queue is not None:
            debug(f"iowrite got request {pv_name},{value}")
            self.io_put_queue.put({pv_name: value})
        else:
            debug(f"no IO is linked to the device. Couldn't process {pv_name}")

    def ioread(self, pv_name = None, value = None):
        """
        put dictionary of key:value pairs to IO.

        Parameters
        ----------
        pv_dict:  (dictionary)
            dictionary of PVs and new PV values

        Returns
        -------

        Examples
        --------
        >>> device.ioput(pv_name = '.running',value = False)

        """
        raise NotImplementedError

    def ioexecute(self, pv_name = None, value = None, **kwargs):
        """
        executes command arrived from IO

        Parameters
        ----------
        pv_name:  (string)
            string name of the PV
        value:  (string,list,integer,float,array)
            the new value to be submitted to io for processing.

        Returns
        -------

        Examples
        --------
        >>> device.ioexecute(pv_name = '.running',value = False)

        """
        print(f"ioexecute received: {pv_name},{value}")
        if pv_name == 'VAL':
            print(value,type(value))
            if type(value) == float:
                self.move_abs(value)
            else:
                warning(f'the input value {pv_name} for PV {value} is not float')
        if pv_name == 'VELO':
            print(value,type(value))
            if type(value) == float:
                self.set_speed_on_the_fly(value)
            else:
                warning(f'the input value {pv_name} for PV {value} is not float')
        if pv_name == 'VALVE':
            print(f'{value},{type(value)}')
            value = value.lower()
            if value == 'o' or value == 'i' or value == 'b':
                self.set_valve(value)
            else:
                warning(f'the input value {pv_name} for PV {value} is not float')
        if pv_name == 'CMD':
            print(f'{value},{type(value)}')



####################################################################################################
### device specific functions
####################################################################################################
    def home(self):
        with self.lock:
            self.set_status('homing...')
            self.driver.home()
            self.iowrite(".cmd_HOME",value = 0)
            self.iowrite(".VELO",value = self.speed)
            self.iowrite(".VAL",value = self.cmd_position)
            self.set_status('homing complete')

    def get_position(self):
        """
        request position of the pump via driver

    	Parameters
    	----------

    	Returns
    	-------
        value: float
            current pump position

    	Examples
    	--------
    	>>> device.get_position()
        0.0
        """
        from numpy import nan, zeros
        reply = self.driver._get_position()
        value = self.process_driver_reply(reply)
        if value is None:
            value = nan
        self.position = round(float(value),3)
        arr = zeros((1,2))
        arr[0,0] = time()
        arr[0,1] = self.position
        self.buffers['position'].append(arr)
        return self.position

    def set_position(self, value):
        self.set_cmd_position(value)

    def get_cmd_position(self):
        """
        get commanded position of the pump

    	Parameters
    	----------

    	Returns
    	-------
        value: float
            last known commanded position

    	Examples
    	--------
    	>>> device.get_cmd_position()
        0.0
        """
        return self.cmd_position
    def set_cmd_position(self,value):
        """
        set commanded position of the pump

    	Parameters
    	----------
        value: float
            last known commanded position

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.set_cmd_position(value = 25.0)
        """
        reply = self.driver._set_position(value)
        self.cmd_position = value
        self.scan_period = 0.001

    def get_speed(self):
        """
        read speed from the pump

    	Parameters
    	----------

    	Returns
    	-------
        speed: float
            returns pump speed

    	Examples
    	--------
    	>>> device.get_speed()
        25.0
        """
        reply  = self.driver.get_speed()
        self.speed = self.process_driver_reply(reply)
        return self.speed

    def set_speed_on_the_fly(self,value):
        """
        sets speed on the fly. speed values above 68.8 will be ignored.

    	Parameters
    	----------
        speed: float
             pump speed

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.set_speed_on_the_fly(25.0)
        """
        reply = self.driver._set_speed_on_the_fly(value)
        debug(f'reply: {reply}')
        temp = self.process_driver_reply(reply)
        debug(f'set_speed_on_the_fly: {reply}, {temp}')
        self.speed = value
        debug(f'set_speed_on_the_fly: {self.speed}')

    def set_speed(self,value):
        """
        sets speed of the pump. no limits on the input value

    	Parameters
    	----------
        speed: float
             pump speed

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.set_speed(25.0)
        """
        reply = self.driver.set_speed(value)
        temp = self.process_driver_reply(reply)
        self.speed = value

    def set_status(self, value = ''):
        value = str(value)
        self.iowrite('.STATUS', value)
        self.status = value

    def isdonemoving(self):
        """
        return flag if motion is complete. It will compare the cmd_position and actual position

    	Parameters
    	----------

    	Returns
    	-------
        flag: boolean
            boolean if motor is moving or not

    	Examples
    	--------
    	>>> device.isdonemoving()
        True
        """
        flag = abs(self.cmd_position - self.position) < self.dpos
        return flag

    @property
    def moving(self):
        """
        an alias for busy
        """
        response = self.busy
        return response

    def move_abs(self,position = 0, speed = None):
        self.driver.abort()
        if speed is None:
            speed = self.speed
        self.scan_period = 0.001
        self.cmd_position = position
        response = self.driver.move_abs(position = position, speed = speed)
        return response

    def get_valve(self):
        """
        reads valve orientation from the pump

    	Parameters
    	----------

    	Returns
    	-------
        valve: string
            valve orientation as a string" 'i','o','b'

    	Examples
    	--------
    	>>> device.get_valve()
        'i'
        """
        reply = self.driver.valve
        value = self.process_driver_reply(reply)
        self.valve = value
        return value

    def set_valve(self,value):
        """
        writes valve orientation into the pump

    	Parameters
    	----------
        valve: string
            valve orientation as a string" 'i','o','b'

    	Returns
    	-------

    	Examples
    	--------
    	>>> device.get_valve('i')
        """
        self.driver.set_valve(value)
        self.valve = value


    def process_driver_reply(self,reply):
        """
        waits for the syringe to finish the previous task. The while loop checks every dt for the status of the syringe pump.

        Parameters
        ----------
        dt: float
            period in seconds at which the ump status is checked.

        Returns
        -------

        Examples
        --------
        >>> reply = {'value': '', 'error_code': '`', 'busy': False, 'error': 'No Error'}
        >>> device.process_driver_reply(reply)
        """
        from time import time
        debug('process_driver_reply')
        if reply is not None:
            self.busy = reply['busy']
            self.error_code = reply['error_code']
            self.error = reply['error']
            self.last_reply_process = time()
            value = reply['value']
            if False:
                self.iowrite("MOVN",value = self.moving)
                self.iowrite("ERROR",value = self.error)
                self.iowrite("ERROR_CODE",value = self.error_code)
            elif False:
                self.iowrite("ERROR",value = 'Communication Error')
                self.iowrite("ERROR_CODE",value = '!')
        else:

            logging.warning('warning in process_driver_reply: reply = {}'.format(reply))
            value = None
        return value

    def get_alarm(self):
        """
        returns integer if alarm conditions are met
        """
        if self.position <= self.low_level_limit_alarm:
            string = 'current position {} below low level limit {}'.format(self.position, self.low_level_limit_alarm)
        else:
            string = ''
        return string

    def get_warning(self):
        """
        returns integer if alarm conditions are met
        """
        if self.position <= self.low_level_limit_warning:
            flag = 'current position {} below low level limit {}'.format(self.position, self.low_level_limit_warning)
        else:
            flag = ''
        return flag

    #Compound actions

    def wait(self, dt = 0.34):
        """
        waits for the syringe to finish the previous task. The while loop checks every dt for the status of the syringe pump.

        Parameters
        ----------
        dt: float
            period in seconds at which the ump status is checked.

        Returns
        -------

        Examples
        --------
        >>> device.wait(dt = 0.34)
        """
        busy = self.get_busy()
        while self.busy:
            sleep(dt)
        busy = self.get_busy()

    def prime(self, N = 5):
        """
        performs safe compound "prime" command which empties and fills the  syringe N times The final state of the valve is 'out'. The final state of the syringe is full.

        Parameters
        ----------
        N: ingteger
            number of times to empty and fill. Default = 5 which is good enough.

        Returns
        -------

        Examples
        --------
        >>> device.empty()
        """
        start_speed = self.speed
        self.set_speed(68.0)
        self.set_valve('i')
        self.wait()
        for i in range(N):
            self.set_cmd_position(0.0)
            self.wait()
            self.set_cmd_position(250.0)
            self.wait()
        self.set_speed(start_speed)
        self.set_valve('o')
        busy = self.get_busy()


    def empty(self):
        """
        performs safe compound "empty" command which empties the syringe with fluid back into the reservour. The final state of the valve is 'out'.

        Parameters
        ----------

        Returns
        -------

        Examples
        --------
        >>> device.empty()
        """

        start_speed = self.speed
        self.set_speed(100.0)
        self.set_valve('i')
        self.wait()
        self.set_cmd_position(0.0)
        self.wait()
        self.set_speed(start_speed)
        self.set_valve('o')

    def fill(self):
        """
        performs safe compound "fill" command which refills the syringe with fluid from the reservour. The final state of the valve is 'out'.

        Parameters
        ----------

        Returns
        -------

        Examples
        --------
        >>> device.fill()
        """
        start_speed = self.speed
        self.set_speed(100.0)
        self.set_valve('i')
        self.wait()
        self.set_cmd_position(0.0)
        self.wait()
        self.set_cmd_position(250.0)
        self.wait()
        self.set_speed(start_speed)
        self.set_valve('o')

    def flow(self,position = 0, speed = 0.1):
        """
        performs safe compound "flow" command which initits flow towards posotion with the given speed. Makes sure to set the valve orientation to 'o' output.

        Parameters
        ----------

        Returns
        -------

        Examples
        --------
        >>> device.flow(position = 25, speed = 0.1)
        """
        self.abort()
        if self.valve is not 'o':
            self.set_valve('o')
        if speed <= self.flow_speed_high_limit:
            reply = self.move_abs(position = position, speed = speed)
            self.process_driver_reply(reply)
        else:
            warning('the flow command received speed {} large than flow_speed_high_limit {}'.format(speed,self.flow_speed_high_limit))

    def create_low_pressure(self,N = 1):
        """
        performs safe compound "create_low_pressure" command which creates low pressure in syringe pump #2.

        Parameters
        ----------

        Returns
        -------

        Examples
        --------
        >>> device.create_low_pressure(N = 1)
        """
        from time import sleep
        self.abort()
        for i in range(N):
            self.set_valve('i')
            sleep(0.3)
            while self.busy:
                sleep(0.1)

            self.move_abs(250,65)
            sleep(1)
            while self.busy:
                sleep(0.1)

            self.set_valve('o')
            sleep(0.3)
            while self.busy:
                sleep(0.1)

            self.move_abs(0,65)
            sleep(1)
            while self.busy:
                sleep(0.1)




    def parse_cmd_string(self,string):
        """
        """
        raise NotImplementedError

    def execute_cmd(self,command):
        """
        executes command from CMD(command) PV.

        Parameters
        ----------
        command: string

        Returns
        -------

        Examples
        --------
        >>> device.execute_cmd(command = 'exec:flow(position = 25,speed = 0.1)')
        """
        raise NotImplementedError

if __name__ == "__main__": #for testing
    from tempfile import gettempdir
    import logging
    logging.basicConfig(filename=gettempdir()+'/syringe_pump_DL.log',
                        level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
    pump = Device()
    print("pump.init(2,0.1,100,'Z',250)")
    print("pump.start()")
