class ServerParent:
    def __init__(self, **kwargs):
        pass

    def toCallChild(self):
        print("Called Parent")

    def parentCall(self,called = None):
        print("Primay call...")
        if called == None:
            self.toCallChild()
        else:
            super(called,self).toCallChild()

    

class ServerChild(ServerParent):
    def __init__(self, **kwargs):
        super().__init__()
    
    def toCallChild(self):
        print("Called child")

    def parentCall(self):
        super().parentCall()



if __name__ == "__main__":
    #temp = ServerParent()

    # print(temp.a,temp.b,temp.c)

    temp1 = ServerChild()

    temp1.parentCall()