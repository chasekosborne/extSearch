#!/usr/bin/python
from authServer import hashCompute
from time import time

if __name__ == "__main__":
    print("Input in order: LocalHash/AuthHead(,Tail),timestamp,challenge ")
    print("Current time :",time())
    key = input("1 >")
    timestamp = input("2 >")
    challenge = input("3 >")

    print(hashCompute(key,timestamp,challenge))


