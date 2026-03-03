##### Alex Tregub
##### 2026-03-02
##### Python 3.14.3
##### Authentication interface
##### ===========
# from Crypto.PublicKey import ECC # Recommended as smaller,faster ops

class Authent:
    config = {
        "pubKey":None,
        "privKey":None,
    }



    def __init__(self): # Internal DB init+connect, setup if necessary. Load/INIT SERVERpub+priv keys. (Allowed to 'lose' priv key). Setup for incoming connections
        if (config["pubKey"] or config["privKey"] is None):
            # createServerKeys()
            pass
        
        pass



    #### Internal
    # Key pairs
    def createServerKeys(self): # Gen pub+priv pair
        # serverKey = ECC.generate(curve='p256')
        # config["pubKey"] = serverKey.public_key()
        # config["privKey"] = serverKey
        pass

    def loadServerKeys(self): # Load from config?
        pass

    def decPrivMessage(self): # Decrypt message encrypted via public
        pass
    


    #### DB Management
    # DB connections...
    def createDbs(self): # Create + connect Dbs [(userId,email,salt,salt-hash_pass),(userId,expiry,authHead,authTail),...]
        pass

    def connectDbs(self): # Connect Dbs [UserAuth,TokenAuth]
        pass

    def userAuthAdd(self): # Create user: needs email,salt,salt-hash_pass
        pass

    def userAuthQuery(self): # Find user: return all (uid,email,salt,salt-hash_pass)
        pass

    def userAuthRemove(self): # Remove user: by id
        pass


    def tokenAuthAdd(self): # Add token+userid
        pass

    def tokenAuthQuery(self): # Find token by userid/authHead
        pass

    def tokenAuthRemove(self): # Remove token by userid/authHead
        pass

    def tokenAuthPurge(self): # Check + invalidate all expired tokens
        pass



    #### Networked
    def getServerPubKey(self): # Return SERVER public key, assumes loaded/created
        pass

    def signupUser(self): # SYNCHRONOUS process
        pass

    def loginUser(self): # SYNCHRONOUS process (returns auth token)
        pass

    def validateAuthToken(self): # ASYNC process, not necessarily called by external 
        pass