#!/usr/bin/env python3
import termios
import fcntl
import sys
import os
import threading
import atexit
import time
from datetime import datetime
import itertools
from logging import debug,info,warn,error
#Input/Output server library
from caproto.server import pvproperty, PVGroup, ioc_arg_parser, run

from ubcs_auxiliary.threading import new_thread

from numpy import zeros, random, nan
class ServerIO(PVGroup):
    RBV = pvproperty(value=nan, units = 'uL', read_only = True)
    VAL = pvproperty(value=nan, units = 'uL')
    VELO = pvproperty(value=nan, units = 'uL/s')
    VALVE = pvproperty(value='')

    # NOTE the decorator used here:
    @RBV.startup
    async def RBV(self, instance, async_lib):
        # This method will be called when the server starts up.
        debug('* request method called at server startup')
        self.io_get_queue = async_lib.ThreadsafeQueue()
        self.io_put_queue = async_lib.ThreadsafeQueue()
        pump1.io_put_queue = self.io_put_queue
        pump1.io_get_queue = self.io_get_queue

        # Loop and grab items from the response queue one at a time
        while True:
            value = await self.io_put_queue.async_get()
            debug(f'Got put request from the device: {value}')
            if 'RBV' in list(value.keys()):
                await self.RBV.write(value['RBV'])
            elif 'VAL' in list(value.keys()):
                await self.VAL.write(value['VAL'])
            elif 'VELO' in list(value.keys()):
                await self.VELO.write(value['VELO'])
    @VAL.putter
    async def VAL(self, instance, value):
        print('Received update for the {}, sending new value {}'.format('VAL',value))
        pump1.ioexecute(pv_name = 'VAL', value = float(value))
        return value

    @VELO.putter
    async def VELO(self, instance, value):
        print('Received update for the {}, sending new value {}'.format('VELO',value))
        pump1.ioexecute(pv_name = 'VELO', value = float(value))
        return value

    @VALVE.putter
    async def VALVE(self, instance, value):
        print('Received update for the {}, sending new value {}'.format('VALVE',value))
        pump1.ioexecute(pv_name = 'VALVE', value = value)
        return value
from syringe_pump.device import Device
#pump1 = Device()
#pump1.init(1,0.1,100,'Y',250)
#pump1.start()

pump1 = Device()
pump1.init(1,0.1,100,'Y',250)
pump1.start()

if __name__ == '__main__':
    from tempfile import gettempdir
    import logging
    print(gettempdir()+'/syringe_pump_device_io.log')
    logging.basicConfig(filename=gettempdir()+'/syringe_pump_device_io.log',
                        level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
    debug('test write debug')
    ioc_options, run_options = ioc_arg_parser(
        default_prefix='NIH:SYRINGE1.',
        desc='Run an IOC that does blocking tasks on a worker thread.')

    ioc = ServerIO(**ioc_options)
    run(ioc.pvdb, **run_options)
