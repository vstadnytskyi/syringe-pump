#!/usr/bin/env python3

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

class Server(PVGroup):
    RBV = pvproperty(value=nan, units = 'uL', read_only = True, precision = 3)
    VAL = pvproperty(value=nan,
                    units = 'uL',
                    precision = 3,
                    upper_ctrl_limit=250.0,
                    lower_ctrl_limit=0.0,)
    VELO = pvproperty(value=nan,
                        units = 'uL/s',
                        precision = 3,
                        upper_ctrl_limit=68.0,
                        lower_ctrl_limit=0.001)
    VALVE = pvproperty(value='', dtype=str, max_length=2)
    CMD = pvproperty(value='', max_length=1000, dtype=str)
    ACK = pvproperty(value='', max_length=1000, dtype=str, read_only = True)
    #MOVN",value = self.moving)
    #ERROR
    #ERROR_CODE
    STATUS = pvproperty(value='unknown', max_length=10, dtype=str, read_only = True)

    device = None

    # NOTE the decorator used here:
    @RBV.startup
    async def RBV(self, instance, async_lib):
        # This method will be called when the server starts up.
        debug('* request method called at server startup')
        self.io_get_queue = async_lib.ThreadsafeQueue()
        self.io_put_queue = async_lib.ThreadsafeQueue()
        self.device.io_put_queue = self.io_put_queue
        self.device.io_get_queue = self.io_get_queue

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
            elif 'VALVE' in list(value.keys()):
                await self.VALVE.write(value['VALVE'])

    #@VAL.startup
    #async def VAL(self, instance, async_lib):
    #    self.VAL.value = self.device.get_cmd_position()

    @VAL.putter
    async def VAL(self, instance, value):
        print('Received update for the {}, sending new value {}'.format('VAL',value))
        await self.device_ioexecute(pv_name = 'VAL', value = float(value))
        return value

    @VELO.putter
    async def VELO(self, instance, value):
        print('Received update for the {}, sending new value {}'.format('VELO',value))
        await self.device_ioexecute(pv_name = 'VELO', value = float(value))
        return value

    @VALVE.putter
    async def VALVE(self, instance, value):
        print('Received update for the {}, sending new value {}'.format('VALVE',value))
        await self.device_ioexecute(pv_name = 'VALVE', value = value)
        return value

    @CMD.putter
    async def CMD(self, instance, value):
        print('Received update for the {}, sending new value {}'.format('CMD',value))
        await self.device_ioexecute(pv_name = 'CMD', value = value)
        return value

    async def device_ioexecute(self, pv_name, value):
        """
        """
        if self.device is not None:
            self.device.ioexecute(pv_name = pv_name, value = value)

    async def device_ioread(self, pv_name, value):
        """
        """
        pass

    def update_pvs(self):
        """
        Force update of all PVs. Works only if self.device is assigned. If None, nothing will happen.
        """
        if self.device is not None:
            pass
        else:
            pass

class Device_IO(object):
    def __init__(self, pump_id):
        """

        """
        from syringe_pump.device import Device
        import sys
        if pump_id == 1 or pump_id == 3:
            orientation = 'Y'
        elif pump_id == 2 or pump_id == 4:
            orientation = 'Z'
        pump = Device()
        pump.init(pump_id,0.1,100,orientation,250)
        pump.start()

        from tempfile import gettempdir
        import logging
        filename=gettempdir()+f'/syringe_pump_device_io_{pump_id}.log'
        print(filename)
        logging.basicConfig(filename=filename,
                            level=logging.DEBUG,
                            format="%(asctime)s %(levelname)s %(module)s.%(funcName)s: %(message)s")
        debug('test write debug')
        ioc_options, run_options = ioc_arg_parser(
            default_prefix=f'NIH:SYRINGE{pump_id}.',
            desc='Run an IOC that does blocking tasks on a worker thread.')

        ioc = Server(**ioc_options)
        ioc.device = pump
        run(ioc.pvdb, **run_options)

def run_ioc(pump_id = 2):
    from syringe_pump import device_io
    import multiprocessing
    p = multiprocessing.Process(target=device_io.Device_IO,args=(pump_id,))
    p.start()
    return p

if __name__ == '__main__':
    pump_id = 1
    from syringe_pump.device import Device
    import sys
    if pump_id == 1 or pump_id == 3:
        orientation = 'Y'
    elif pump_id == 2 or pump_id == 4:
        orientation = 'Z'
    pump = Device()
    pump.init(pump_id,0.1,100,orientation,250)
    pump.start()

    from tempfile import gettempdir
    import logging
    logfile = gettempdir()+f'/syringe_pump_device_io_{str(pump_id)}.log'
    logging.basicConfig(level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(module)s.%(funcName)s: %(message)s",
        filename=logfile,
    )
    debug('test write debug')
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=f'NIH:SYRINGE{str(pump_id)}.',
        desc='Run an IOC that does blocking tasks on a worker thread.')

    ioc = Server(**ioc_options)
    ioc.device = pump
    ioc.update_pvs()
    #This is were start_up happens!
    run(ioc.pvdb, **run_options)
