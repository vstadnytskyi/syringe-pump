#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Cavro Centris Syringe pump device
author: Valentyn Stadnytskyi
Created: May 28 2019
Last modified: May 28 2019
"""

__version__ = '0.0.0'

from .driver import Driver


import traceback
from pdb import pm
import psutil, os
import platform #https://stackoverflow.com/questions/110362/how-can-i-find-the-current-os-in-python


from numpy import nan, mean, std, nanstd, asfarray, asarray, hstack, array, concatenate, delete, round, vstack, hstack, zeros, transpose, split, unique, nonzero, take, savetxt, min, max

from time import time, sleep, clock
import sys
import os.path
import struct
from pdb import pm
from time import gmtime, strftime, time
from logging import debug,info,warning,error
from ubcs_auxiliary.threading import new_thread
from struct import pack, unpack
from timeit import Timer, timeit


class Device(object):

    """circular buffers dictionary contains information about all circular buffers and their type (Server, Client or Queue)"""
    circular_buffers = {}

    def __init__(self):
        #Thread.__init__(self)
        self.running = False
        #self.daemon = False # OK for main thread to exit even if instance is still running
        self.description = ''

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

#  ############################################################################
#  Basic IOC operations
#  ############################################################################
    def first_time_setup(self):
        """default factory setting or first time setup"""
        raise NotImplementedError

    def init(self, pump_id = None,speed = None, backlash = None, orientation = None, volume = None):
        """
        initialize the server\IOC
        """
        from threading import RLock as Lock
        self.lock = Lock()
        from drivers.Cavro_Centris_Syringe_Pump.cavro_centris_syringe_pump_driver import Driver
        self.pump_id = pump_id
        self.driver = Driver()
        self.name = 'NIH_syringe_pump_'+ str(pump_id)
        self.prefix = 'NIH:SYRINGE' + str(pump_id)
        if pump_id is not None:
            self.driver.init(pump_id, speed = speed, backlash = backlash, orientation = orientation, volume = volume)
            self.speed = speed
            self.cmd_position = 0.0
            self.valve = 'o'
            self.startup()
            self.run_once()


    def abort(self):
        """orderly abort of the current operation"""
        from CAServer import casput
        with self.lock:
            #self.set_status('aborting...')
            reply = self.driver.abort()
            self.process_driver_reply(reply)
            prefix = self.prefix
            t1 = time()
            flag = True
            while self.get_busy():
                sleep(0.1)
                if time() - t1 > 10.0:
                    flag = False
                    break
            if flag:
                casput(prefix+".cmd_ABORT",value = 0)
                #casput(prefix+".VAL",value = self.position)
                #self.set_status('')
                #self.set_status('aborted')

    def close(self):
        """orderly close\shutdown"""
        self.stop()
        self.abort()
        self.cleanup()
        self.driver.close()

    def help(self):
        """returns help  information in a string format."""
        raise NotImplementedError

    def snapshot(self):
        """returns snapshot of current PVs and their values in a dictionary format"""
        raise NotImplementedError

    def start(self):
        """starts a separate thread"""
        from thread import start_new_thread
        start_new_thread(self.run,())

    def stop(self):
        """stop a separate thread"""
        from CAServer import casput
        self.running = False
        casput(self.prefix+".RUNNING",value = self.running, update = False)


    def run_once(self):
        """
        """
        from CAServer import casput
        #request current position from the syringe pump
        self.position = self.get_position()
        if not self.busy:
            self.scan_period = 10.0
        casput(self.prefix+".DMOV",value = self.isdonemoving(), update = False)
        casput(self.prefix+".RBV",value = self.position, update = False)
        casput(self.prefix+".ALARM",value = self.get_alarm(), update = False)
        casput(self.prefix+".WARN",value = self.get_warning(), update = False)


    def run(self):
        """"""
        from CAServer import casput
        self.running = True
        casput(self.prefix+".RUNNING",value = self.running, update = False)

        while self.running:
            t = time()
            self.run_once()
            while time() - t < self.scan_period:
                sleep(0.1)

        self.running = False
        casput(self.prefix+".RUNNING",value = self.running, update = False)

    def get_busy(self):
        reply = self.driver.busy()
        value = self.process_driver_reply(reply)
        if value is not None:
            return bool(int(self.process_driver_reply(reply)))
        else:
            return None

    def IOC_run(self):
        """"""
        raise NotImplementedError




    def startup(self):
        from CAServer import casput, casmonitor, PV_names
        from pickle import dumps as dump_string
        info('startup for pump {}'.format(self.pump_id))
        prefix = self.prefix

        #Indicator PVs
        casput(prefix+".DESC",value = self.description, update = False)
        casput(prefix+".EGU",value = "uL")
        casput(prefix+".ALARM",value = '')
        casput(prefix+".WARN",value = '')
        casput(prefix+".LLIM_ALARM",value = self.low_level_limit_alarm)
        casput(prefix+".LLIM_WARN",value = self.low_level_limit_warning)
        casput(prefix+".RUNNING",value = self.running, update = False)
        casput(prefix+".RBV",value = self.position)
        casput(prefix+".LIST_ALL_PVS", value = self.list_all_pvs())

        #Control PVs
        casput(prefix+".CMD",value = dump_string(''))
        casmonitor(prefix+".CMD",callback=self.command_monitor)

        casput(prefix+".VAL",value = self.cmd_position)
        casmonitor(prefix+".VAL",callback=self.monitor)


        casput(prefix+".VELO",value = self.speed*1.0)
        casmonitor(prefix+".VELO", callback=self.monitor)

        casput(prefix+".VALVE",value = self.valve)
        casmonitor(prefix+".VALVE", callback=self.monitor)

        from auxiliary.circular_buffer_LL import CBServer as Server
        self.buffers = {}
        self.buffers['position'] = Server(size = (2,1*3600*2) , var_type = 'float64')

    def monitor(self,PV_name,value,char_value):
        """Process PV change requests"""
        from CAServer import casput
        info("monitor: %s = %r" % (PV_name,value))
        if PV_name == self.prefix + ".VAL":
            self.set_cmd_position(value)
        if PV_name == self.prefix + ".VELO":
            self.set_speed_on_the_fly(value)
        if PV_name == self.prefix + ".VALVE":
            self.set_valve(value)

    def command_monitor(self,PV_name,value,char_value):
        """Process PV change requests"""
        from CAServer import casput
        from pickle import loads
        info("command_monitor: %s = %r" % (PV_name,value))
        cmd_dict = {'abort':[],
                    'fill':[],
                    'empty':[],
                    'prime':['N'],
                    'flow':['position','speed']
                    }
        if PV_name == self.prefix+".CMD":
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


        #if PV_name == self.prefix+".cmd_HOME":
        #   self.home()



    def cleanup(self):
        from CAServer import casdel
        for pv in self.list_all_pvs():
            casdel(pv)

    def list_all_pvs(self):
        from CAServer import PVs
        result = list(PVs.keys())
        return result


####################################################################################################
### device specific functions
####################################################################################################
    def home(self):
        with self.lock:
            self.set_status('homing...')
            if value == 1:
                self.driver.home()
            casput(prefix+".cmd_HOME",value = 0)
            casput(prefix+".VELOCITY",value = self.cmd_position)
            casput(prefix+".VAL",value = self.speed)
            self.set_status('homing complete')

    def get_position(self):
        """
        request position of the pump
        """
        from numpy import nan
        reply = self.driver._get_position()
        value = self.process_driver_reply(reply)
        if value is None:
            value = nan
        self.position = round(float(value),3)
        return self.position

    def set_position(self, value):
        with lock:
            self.set_cmd_position(value)

    def get_cmd_position(self):
        """
        get position of the pump
        """
        return self.cmd_position
    def set_cmd_position(self,value):
        from CAServer import casput
        reply = self.driver._set_position(value)
        self.cmd_position = value
        self.scan_period = 0.001
        casput(self.prefix+".VAL", self.cmd_position, update = False)

    def get_speed(self):
        """
        get position of the pump
        """
        reply  = self.driver.get_speed()
        self.speed = self.process_driver_reply(reply)
        casput(self.prefix+".VELO", self.speed , update = False)
        return self.speed

    def set_speed_on_the_fly(self,value):
        from CAServer import casput
        reply = self.driver._set_speed_on_the_fly(value)
        temp = self.process_driver_reply(reply)
        print('set_speed_on_the_fly: {}, {}'.format(reply,temp))
        self.speed = value
        casput(self.prefix+".VELO", self.speed , update = False)


    def set_speed(self,value):
        """
        set speed of the pump
        """
        from CAServer import casput
        reply = self.driver.set_speed(value)
        temp = self.process_driver_reply(reply)
        self.speed = value
        casput(self.prefix+".VELO", self.speed , update = False)

    def set_status(self, value = ''):
        from CAServer import casput
        value = str(value)
        casput(self.prefix + '.STATUS', value, update = False)
        self.status = value

    def isdonemoving(self):
        """
        return flag if motion is complete. It will compare the cmd_position and actual position
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
        reply = self.driver.valve
        value = self.process_driver_reply(reply)
        self.valve = value
        return value

    def set_valve(self,value):
        from CAServer import casput
        self.driver.set_valve(value)
        self.valve = value
        casput(self.prefix+".VALVE", value)
        sleep(0.2)


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
        >>> d
        """
        if reply is not None:
            self.busy = reply['busy']
            self.error_code = reply['error_code']
            self.error = reply['error']
            value = reply['value']
        #update CA Server with new values
            casput(self.prefix+".MOVN",value = self.moving, update = False)
            casput(self.prefix+".ERROR",value = self.error, update = False)
            casput(self.prefix+".ERROR_CODE",value = self.error_code, update = False)
        else:
            casput(self.prefix+".ERROR",value = 'Communication Error', update = False)
            casput(self.prefix+".ERROR_CODE",value = '!', update = False)
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
        self.abort()
        if self.valve is not 'o':
            self.set_valve('o')
        if speed <= self.flow_speed_high_limit:
            self.move_abs(position = position, speed = speed)

if __name__ == "__main__": #for testing
    from tempfile import gettempdir
    import logging
    logging.basicConfig(filename=gettempdir()+'/syringe_pump_DL.log',
                        level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")


    tower.init()
    tower.start()
    #tower.run()
