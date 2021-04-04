=====
Usage
=====

Start by importing Cavro Centris Syringe Pump.

.. code-block:: python

    >>> proc = []
    >>> from syringe_pump.device_io import Server, Device_IO, run_ioc
    >>> for i in range(4):
        proc.append(run_ioc(pump_id = i+1))
