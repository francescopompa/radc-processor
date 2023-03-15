

import time
from receiver_class import Receiver

#
# Todo:
# Lock __main__ in try/except to catch keyboard interrupt?
#

def main(runtime=20):
    with Receiver() as rec:
        rec.start()
        print(f"Idling {runtime} seconds...")
        time.sleep(runtime)
        # rec.stop()

    print("Finished")

if __name__ == "__main__":
    main()