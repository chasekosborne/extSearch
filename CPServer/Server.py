import asyncio
from collections import deque
from Utilities import checkAllCollisions,checkBounds

class ServerParent():
    def checkAuth(self, auth, data):
        pass

    def push(self, data):
        pass

    def pop(self):
        pass

    def process_next(self):
        pass

    def validate(self, data):
        pass


class CPServer(ServerParent):
    def __init__(self):
        self.submissionQueue = deque()

    def checkAuth(self, auth, data):
        if auth:
            print("Auth successful. Adding to queue.")
            self.push(data)
            return True
        else:
            print("Auth failed. Dropping data.")
            return False

    def push(self, data):
        self.submissionQueue.append(data)

    def pop(self):
        if self.submissionQueue:
            return self.submissionQueue.popleft() 
        return None 

    def process_next(self):
        data = self.pop()
        if data:
            self.validate(data) 

    def validate(self, data):
        if data:
            squareSize = data[0]['square_size']
            Collision = (checkAllCollisions(data, squareSize)[0])
            if Collision:
                print("Invalid Data")
                return;
            
            print(checkBounds(data)) ## Square Bounds

            ## Check if all squareSize the same???
            ## MUST CHANGE DATA BEFORE SEENDING TO DB, 
            ## Send Data to DataBase??

            # deployBtn.addEventListener('click', async () => {
            # const data = [];
            # for (let sq of squares) {
            #     const squareCorners = getSquareCorners(sq);
            #     const organizedBounds = organizeSquareBounds(squareCorners);
            #     data.push([organizedBounds.top,organizedBounds.right,organizedBounds.bottom,organizedBounds.left]);
            # }

