import asyncio
from collections import deque

class CPServer:
    def __init__(self):
        self.submissionQueue = deque()
        pass
    
    def push(self,data):
        self.submissionQueue.append(data)
        self.validate()

    def pop(self):
        if self.submissionQueue:
            return self.submissionQueue.popleft() 
        else:
            return None 

    def validate(self):
        data = self.pop()
        for box in data:
            pass
            ## LOGIC TO CHECK IT IN BOUND AND SQUARES NOT OVERLAPPING
    



    
server = CPServer()
