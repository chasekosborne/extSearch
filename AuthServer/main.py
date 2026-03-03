#!/usr/bin/python
##### Alex Tregub
##### 2026-03-02
##### Python 3.14.3
##### Authentication interface
##### ===========
#     !!! KEYS SAVED WITH NO PASSWORD. DISK ACCESS MEANS COMPROMISED PRIVATE KEY. DO. NOT. UPLOAD. PRIVATE KEYS TO GITHUB.
##### ===========
# from Crypto.PublicKey import ECC # Recommended as smaller,faster ops
from cryptography.hazmat.primitives.asymmetric import rsa # RSA used for pub/priv keys
from cryptography.hazmat.primitives import serialization # export
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

class Authent:
    config = {
        "pubFile":"./pub.pem",
        "privFile":"./priv.pem",
    }
    pubKey = None
    privKey = None



    def __init__(self): # Internal DB init+connect, setup if necessary. Load/INIT SERVERpub+priv keys. (Allowed to 'lose' priv key). Setup for incoming connections
        try:
            self.loadServerKeys()
        except:
            print("Failed loading Pub+Priv keys.")
            self.createServerKeys()
    # END



    #### Internal
    # Key pairs - NO PASSWORD
    def createServerKeys(self): # Gen pub+priv pair
        self.privKey = rsa.generate_private_key(
            public_exponent = 65537, # https://www.daemonology.net/blog/2009-06-11-cryptographic-right-answers.html, https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/
            key_size=4096 # MIN 2048, DEFAULT 3072, 4096 (112bit,128bit, 150bit respectively)
        )
        self.pubKey = self.privKey.public_key()

        # SAVING TO DISK. DANGEROUS. NO ENCRYPTION USED.
        pemPrivate = self.privKey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        pemPublic = self.pubKey.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
            # encryption_algorithm=serialization.NoEncryption() # Not needed, Public key has no encryption needs...
        )

        with open(self.config["pubFile"],"wb") as file:
            file.write(pemPublic)
        
        with open(self.config["privFile"],"wb") as file:
            file.write(pemPrivate)

        print("Pub+Priv keys successfully CREATED+SAVED.")
    # END

    def loadServerKeys(self): # Load from config
        with open(self.config["privFile"],"rb") as file:
            self.privKey = serialization.load_pem_private_key(
                file.read(),
                password=None
            )

        with open(self.config["pubFile"],"rb") as file:
            self.pubKey = serialization.load_pem_public_key(
                file.read()
            )

        print("Pub+Priv keys successfully loaded.") # DEBUG
    # END

    def decPrivMessage(self,msg): # Decrypt message encrypted via public key
        # ASSUME WE USE OAEP padding, PADDING VIA SHA256, MGF1 used. https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/#encryption
        
        return self.privKey.decrypt(
            msg,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    # END
    


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
        return self.pubKey
    # END

    def signupUser(self): # SYNCHRONOUS process
        pass

    def loginUser(self): # SYNCHRONOUS process (returns auth token)
        pass

    def validateAuthToken(self): # ASYNC process, not necessarily called by external 
        pass



if __name__ == "__main__":
    test = Authent()
    # print(test.privKey,test.pubKey) # NOT LOADING...

    testPubKey = test.getServerPubKey()
    testMsg = testPubKey.encrypt(
        b"TESTED PUBLIC KEY ENC -> PRIVATE DEC",
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    print(test.decPrivMessage(testMsg))

    