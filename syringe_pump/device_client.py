#!/usr/bin/env python3
from caproto.threading.client import Context
prefix='NIH:SYRINGE1.'
ctx = Context()
RBV, VAL = ctx.get_pvs(prefix+'RBV',prefix+'VAL')
VELO, = ctx.get_pvs(prefix+'VELO')
VALVE, = ctx.get_pvs(prefix+'VALVE')
