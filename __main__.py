"AnyWave plugin script"

import os
import sys

# correct filename for AnyWave plugins
__file__ = sys.argv[-1]

# setup path
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
sys.path.insert(0, os.path.join(here, 'deps'))

# setup main window
from seeg_surfer.main import create_main_window
create_main_window()
