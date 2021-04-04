#!/usr/bin/env python3
#import os
#os.environ["EPICS_CA_ADDR_LIST"] = '128.231.5.255
class Client(object):
    RBV = None
    VAL = None
    VELO = None
    VALVE = None
    def __init__(self,prefix):
        from caproto.threading.client import Context
        self.prefix = prefix
        self.ctx = Context()
        self.RBV, = self.ctx.get_pvs(self.prefix+'RBV')
        self.VAL, = self.ctx.get_pvs(self.prefix+'VAL')
        self.VELO, = self.ctx.get_pvs(self.prefix+'VELO')
        self.VALVE, = self.ctx.get_pvs(self.prefix+'VALVE')
if __name__ == '__main__':
    from tempfile import gettempdir
    client = Client('NIH:SYRINGE1.')
    import logging;
    logging.basicConfig(filename=gettempdir()+'/syringe_pump_device_client.log',
                        level=logging.DEBUG,
                        format="%(asctime)s %(levelname)s: %(message)s")
