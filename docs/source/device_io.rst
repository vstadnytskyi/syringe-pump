=========================
Device Level Input-Output
=========================

Start by importing Cavro Centris Syringe Pump input output controller (IOC).

.. code-block:: python

  >>> from syringe_pump.device_io import run_ioc
  >>> process_list = []
  >>> process_list.append(run_ioc(1))
  >>> process_list.append(run_ioc(2))
  >>> process_list.append(run_ioc(3))
  >>> process_list.append(run_ioc(4))


.. autoclass:: syringe_pump.device_io.Server
  :members:

  .. autoclass:: syringe_pump.device_io.Device_IO
    :members:
