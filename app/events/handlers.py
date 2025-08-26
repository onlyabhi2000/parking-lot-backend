from app.events.signals import lot_full, lot_available


def notify_lot_full(sender, lot, **extra):
    print(f"Parking Lot '{lot.name}' is FULL! Notify owner: {lot.owner_name}")

def notify_lot_available(sender, lot, **extra):
    print(f"Parking Lot '{lot.name}' now has space. Notify owner: {lot.owner_name}")

# Connect handlers
lot_full.connect(notify_lot_full)
lot_available.connect(notify_lot_available)
