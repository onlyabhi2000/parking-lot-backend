from blinker import Namespace

# Create a signal namespace
_signals = Namespace()

# Define our signals
lot_full = _signals.signal("lot_full")          
lot_available = _signals.signal("lot_available") 