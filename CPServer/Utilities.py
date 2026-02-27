## Server Side Validation and Queue Management
import math

def vecSub(a,b):
    return [a[0]-b[0],a[1]-b[1]]

def vecDiv(a,c):
    return [a[0]/c,a[1]/c]

def vecDot(a,b):
    return a[0]*b[0] + a[1]*b[1]

#Convert between dict. corners to vec corners:
def convCornersToVec(corners):
    # console.log("Corners: ",corners);
    arr = []
    for corner in corners:
        # console.log([corner.x,corner.y]);
        arr.append([corner['x'],corner['y']])
    return arr

def _checkOverlap(sq1, sq2, sideLength): 
    # Simple vector collision check sq1->sq2 (directional) collision
    
    # Hardcoded 1:A-B check: (square 1)
    aPos = sq1[0] # A point
    bPos = sq1[1]
    dPos = sq1[3]
    
    bVec = vecSub(bPos, aPos) # B vec (A origin relative)
    bHat = vecDiv(bVec, sideLength) # B Norm vec
    
    # Offset sq2 - using list comprehension instead of JS map
    sq2Copy = [vecSub(p, aPos) for p in sq2] # A origin relative vectors for mapping onto line
    # print(sq2Copy)

    # PROJECTION ON B Hat
    sq2Map = [vecDot(bHat, v) for v in sq2Copy] # Gives proj_BHat(*)
    sq2MapSpan = [min(sq2Map), max(sq2Map)] 
    
    if 0 >= sq2MapSpan[1] or sideLength <= sq2MapSpan[0]:
        return False # Never overlaps, exists axis of seperation...

    # Hardcoded 2: A-D check:
    dVec = vecSub(dPos, aPos)
    dHat = vecDiv(dVec, sideLength)

    sq2Map = [vecDot(dHat, v) for v in sq2Copy]
    sq2MapSpan = [min(sq2Map), max(sq2Map)]

    if 0 >= sq2MapSpan[1] or sideLength <= sq2MapSpan[0]:
        return False 

    return True

import math

# Make sure SQUARE_SIZE is defined somewhere at the top of your file!
SQUARE_SIZE = 56 

def getSquareCorners(sq):
    centerX = sq['x'] + SQUARE_SIZE / 2.0
    centerY = sq['y'] + SQUARE_SIZE / 2.0
    
    # Convert degrees to radians
    angle = sq['rotation'] * math.pi / 180.0
    cos_val = math.cos(angle)
    sin_val = math.sin(angle)
    halfSize = SQUARE_SIZE / 2.0
    
    # Returns a list of dictionaries perfectly matching your JS objects
    return [
        {
            'x': centerX + (-halfSize) * cos_val - (-halfSize) * sin_val, 
            'y': centerY + (-halfSize) * sin_val + (-halfSize) * cos_val
        },
        {
            'x': centerX + halfSize * cos_val - (-halfSize) * sin_val, 
            'y': centerY + halfSize * sin_val + (-halfSize) * cos_val
        },
        {
            'x': centerX + halfSize * cos_val - halfSize * sin_val, 
            'y': centerY + halfSize * sin_val + halfSize * cos_val
        },
        {
            'x': centerX + (-halfSize) * cos_val - halfSize * sin_val, 
            'y': centerY + (-halfSize) * sin_val + halfSize * cos_val
        }
    ]


def checkCollides(sq1, sq2, sideLength):
    # Ie. if any return false :: If exists any axis of seperation
    return _checkOverlap(sq1, sq2, sideLength) and _checkOverlap(sq2, sq1, sideLength)


def checkAllCollisions(squaresList, squareSize=SQUARE_SIZE): 
    # Checks for any coliding squares, return list of ids?
    validationList = squaresList
    length = len(validationList)

    # print(validationList, length)

    collis = []
    for i in range(length):
        for j in range(i + 1, length):
            
            # Grabbing the corners and converting them to vectors
            sq1_vec = convCornersToVec(getSquareCorners(validationList[i]))
            sq2_vec = convCornersToVec(getSquareCorners(validationList[j]))
            
            # Checking for collision
            if checkCollides(sq1_vec, sq2_vec, squareSize):
                collis.append([i, j])

    # If the length of collis is greater than 0, it returns True, otherwise False
    return [len(collis) > 0, collis]


def getRotatedSquareBounds(sq):
    squareSize = sq['square_size']
    centerX = sq['x'] + squareSize / 2.0
    centerY = sq['y'] + squareSize / 2.0
    
    angle = sq['rotation'] * math.pi / 180.0
    cos_val = math.cos(angle)
    sin_val = math.sin(angle)
    halfSize = squareSize / 2.0
    
    local_corners = [
        {'x': -halfSize, 'y': -halfSize},
        {'x': halfSize, 'y': -halfSize},
        {'x': halfSize, 'y': halfSize},
        {'x': -halfSize, 'y': halfSize}
    ]
    
    corners = [
        {
            'x': centerX + corner['x'] * cos_val - corner['y'] * sin_val,
            'y': centerY + corner['x'] * sin_val + corner['y'] * cos_val
        }
        for corner in local_corners
    ]
    
    minX = min(corner['x'] for corner in corners)
    minY = min(corner['y'] for corner in corners)
    maxX = max(corner['x'] for corner in corners)
    maxY = max(corner['y'] for corner in corners)
    
    return {
        'minX': minX, 
        'minY': minY, 
        'maxX': maxX, 
        'maxY': maxY
    }



def checkBounds(squares):
    if not squares:
        return {'minX': 0, 'minY': 0, 'maxX': 0, 'maxY': 0}

    minX = float('inf')
    minY = float('inf')
    maxX = float('-inf')
    maxY = float('-inf')
    
    for sq in squares:
        bounds = getRotatedSquareBounds(sq)
        
        minX = min(minX, bounds['minX'])
        minY = min(minY, bounds['minY'])
        maxX = max(maxX, bounds['maxX'])
        maxY = max(maxY, bounds['maxY'])
    maxSide = max((maxX - minX) / SQUARE_SIZE, (maxY - minY) / SQUARE_SIZE)
    precision = 13
    maxSideStr = f"{maxSide:.{precision}f}".rstrip('0').rstrip('.')
    
    return maxSideStr