///// Alex Tregub
///// 2026-02-10
///// collisions.js
///// ===========
/* Provides 'standard' interface for collision checks between squares.
    To be updated later, converted to OO approach...? Keep legacy function
    names as possible.
    - USING STRICT SYNTAX CHECKING, KEEP IF POSSIBLE.
    - (Maj.Min.Rev)
    
    - Working with arrays of corners [A,B,C,D] where A-B A-D adjacent. A is [x,y] array. CONVERSIONS NEEDED

    VERSION 1.0.2 
*/
///// ===========
"use strict";

//// Assumes 2d vec
function vecSub(a,b) { 
    // console.log(a,b);
    return [a[0]-b[0],a[1]-b[1]];
}
function vecDiv(a,c) {
    return [a[0]/c,a[1]/c];
}
function vecDot(a,b) {
    return a[0]*b[0] + a[1]*b[1];
}


//// Convert between dict. corners to vec corners:
function convCornersToVec(corners) {
    // console.log("Corners: ",corners);
    var arr = [];
    for (const corner of corners) {
        // console.log([corner.x,corner.y]);
        arr.push([corner.x,corner.y]);
    }
    return arr;
}


function _checkOverlap(sq1,sq2,sideLength) { // Simple vector collision check sq1->sq2 (directional) collision
    // Hardcoded 1:A-B check: (square 1)
    const aPos = sq1[0]; // A point
    const bPos = sq1[1];
    const dPos = sq1[3];
    var bVec = vecSub(bPos,aPos); // B vec (A origin relative)
    var bHat = vecDiv(bVec,sideLength); // B Norm vec
    
    var sq2Copy = sq2; // Offset sq2
    sq2Copy = sq2Copy.map(p => vecSub(p,aPos)); // UNTESTED; A origin relative vectors for mapping onto line
    // console.log(sq2Copy);

    var sq2Map = sq2Copy.map(v => vecDot(bHat,v)); // UNTESTED; Gives proj_BHat(*)
    var sq2MapSpan = [Math.min(...sq2Map),Math.max(...sq2Map)]; // PROJECTION ON B Hat
    
    if ( (0 >= sq2MapSpan[1]) || (sideLength <= sq2MapSpan[0]) ) { return false; } // Never overlaps, exists axis of seperation...

    // Hardcoded 2: A-D check:
    var dVec = vecSub(dPos,aPos);
    var dHat = vecDiv(dVec,sideLength);

    sq2Map = sq2Copy.map(v => vecDot(dHat,v));
    sq2MapSpan = [Math.min(...sq2Map),Math.max(...sq2Map)]

    if ( (0 >= sq2MapSpan[1]) || (sideLength <= sq2MapSpan[0]) ) { return false; } 

    return true;
}

function checkCollides(sq1,sq2,sideLength) {
    return (_checkOverlap(sq1,sq2,sideLength)) && (_checkOverlap(sq2,sq1,sideLength)); // Ie. if any return false :: If exists any axis of seperation
}

function checkAllCollisions(squaresList,squareSize=SQUARE_SIZE) { // Checks for any coliding squares, return list of ids?
    const validationList = squaresList;
    const len = validationList.length;

    // console.log(validationList,len);

    var collis = []
    for (let i = 0; i < len; ++i) {
        for (let j = i+1; j < len; ++j) {
            if (checkCollides(convCornersToVec(getSquareCorners(validationList[i])),convCornersToVec(getSquareCorners(validationList[j])),squareSize)) {
                collis.push([i,j]);
            }
        }
    }

    return [(collis.length==0 ? false: true),collis];
}