======
Driver
======

Start by importing Cavro Centris Syringe Pump.

.. code-block:: python

  from syringe_pump.driver import Driver
  driver = Driver()
  driver.discover()
  driver
  driver.init(pump_id=1, speed=25, backlash=100, orientation='Y', volume=250)

.. autoclass:: syringe_pump.driver.Driver
  :members:
