
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

from . import driver
from . import device
from . import device_io
from . import device_client
