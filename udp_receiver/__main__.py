

import time
from receiver_class import Receiver


with Receiver() as rec:
    rec.start()
    time.sleep(5)
    rec.stop()

print("Finished")