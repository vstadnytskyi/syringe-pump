=================
Device Level (DL)
=================

Start by importing Cavro Centris Syringe Pump device level code.

.. code-block:: python

  >>> from syringe_pump.device import Device
  >>> p1 = Device()
  >>> p1.init(1,25,100,'Y',250)
  >>> p1.start()
  >>> p1.position
  0.0

.. autoclass:: syringe_pump.device.Device
  :members:
