import asyncio
from collections import deque


class ServerParent:
    def __init__(self, **kwargs):
        pass

    def checkAuth(self,auth,data):
        if(auth):
            self.validate(data)

    def toCallChild(self):
        print("Called Parent")

    def parentCall(self,called):
        print("Primay call...")
        
        super(called,self).toCallChild()



class CPServer(ServerParent):
    def __init__(self):
        super().__init__()
        self.submissionQueue = deque()
    
    def push(self,data):
        self.submissionQueue.append(data)
        self.validate()

    def pop(self):
        if self.submissionQueue:
            return self.submissionQueue.popleft() 
        else:
            return None 

    def validate(self,data):
        print("Validating data...")
        # data = self.pop()
        # for box in data:
        #     pass
        #     ## LOGIC TO CHECK IT IN BOUND AND SQUARES NOT OVERLAPPING
    



    
server = CPServer()
