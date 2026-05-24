import multiprocessing
import time
import sys

def worker():
    sys.exit(1)

if __name__ == '__main__':
    p = multiprocessing.Process(target=worker)
    p.start()
    print("Child started")
    p.join(timeout=600)
    print("Join returned, is_alive:", p.is_alive())
