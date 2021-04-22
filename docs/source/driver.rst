======
Driver
======

This library is designed to handle multiple Cavro Centris syringe pumps connected to one computer. However, there is really no way to identify pumps by their serial number or serial number of RS-232 to USB connectors (Note, some connectors to have serial numbers but it is rear.) The work around is to use the build-in non-volatile memory. (TODO: find a link to a manual and find a page where it is explained to how to write and read from non-volatile memory)

Start by importing Cavro Centris Syringe Pump.

.. code-block:: python

  from syringe_pump.driver import Driver
  driver = Driver()
  driver.discover()
  driver
  driver.init(pump_id=1, speed=25, backlash=100, orientation='Y', volume=250)

.. autoclass:: syringe_pump.driver.Driver
  :members:
