from honeybadgermpc.betterpairing import *
import hashlib
import pickle
from Crypto.Cipher import AES

def polynomial_divide(numerator, denominator):
    temp = list(numerator)
    factors = []
    while len(temp) >= len(denominator):
        diff = len(temp) - len(denominator)
        factor = temp[len(temp) - 1] / denominator[len(denominator) - 1]
        factors.insert(0, factor)
        for i in range(len(denominator)):
            temp[i+diff] = temp[i+diff] - (factor * denominator[i])
        temp = temp[:len(temp)-1]
    return factors

def polynomial_multiply_constant(poly1, c):
    #myzero will be appropriate whether we are in ZR or G
    #myzero = poly1[0] - poly1[0]
    product = [None] * len(poly1)
    for i in range(len(product)):
        product[i] = poly1[i] * c
    return product

def polynomial_multiply(poly1, poly2):
    myzero = ZR(0)
    product = [myzero] * (len(poly1) + len(poly2) -1)
    for i in range(len(poly1)):
        temp = polynomial_multiply_constant(poly2, poly1[i])
        while i > 0:
            temp.insert(0,myzero)
            i -= 1
        product = polynomial_add(product, temp)
    return product

def polynomial_add(poly1, poly2):
    if len(poly1) >= len(poly2):
        bigger = poly1
        smaller = poly2
    else:
        bigger = poly2
        smaller = poly1
    polysum = [None] * len(bigger)
    for i in range(len(bigger)):
        polysum[i] = bigger[i]
        if i < len(smaller):
            polysum[i] = polysum[i] + smaller[i]
    return polysum

def polynomial_subtract(poly1, poly2):
    negpoly2 = polynomial_multiply_constant(poly2, -1)
    return polynomial_add(poly1, negpoly2)
    
# Polynomial evaluation
def f(poly, x):
    assert type(poly) is list
    #previousb = 0
    #k = len(poly) - 1
    #b = 0
    #for (i,coeff) in enumerate(poly):
    #    b = poly[k-i] + previousb * x
    #    previousb = b
    #return b
    y = ZR(0)
    xx = ZR(1)
    for coeff in poly:
        y += coeff * xx
        xx *= x
    return y
    
def interpolate_at_x(coords, x, order=-1):
    ONE = ZR(1)
    if order == -1:
        order = len(coords)
    xs = []
    sortedcoords = sorted(coords, key=lambda x: x[0])
    for coord in sortedcoords:
        xs.append(coord[0])
    S = set(xs[0:order])
    #The following line makes it so this code works for both members of G and ZR
    out = coords[0][1] - coords[0][1]
    for i in range(order):
        out = out + (lagrange_at_x(S,xs[i],x) * sortedcoords[i][1])
    return out

def lagrange_at_x(S,j,x):
    ONE = ZR(1)
    S = sorted(S)
    assert j in S
    #mul = lambda a,b: a*b
    #num = reduce(mul, [x - jj  for jj in S if jj != j], ONE)
    #den = reduce(mul, [j - jj  for jj in S if jj != j], ONE)
    l1 = [x - jj  for jj in S if jj != j]
    l2 = [j - jj  for jj in S if jj != j]
    (num,den) = (ZR(1), ZR(1))
    for item in l1:
        num *= item
    for item in l2:
        den *= item
    return num / den

def interpolate_poly(coords):
    myone = ZR(1)
    myzero = ZR(0)
    #print "IT'SA ME " + str(myzero) + ", THE IDENTITY ELEMENT!"
    #print "Before: " + str(coords[0][1]) + " After: " + str(myzero + coords[0][1])
    poly = [myzero] * len(coords)
    for i in range(len(coords)):
        temp = [myone]
        for j in range(len(coords)):
            if i == j:
                continue
            temp = polynomial_multiply(temp, [ -1 * (coords[j][0] * myone), myone])
            temp = polynomial_divide(temp, [myone * coords[i][0] - myone * coords[j][0]])
        poly = polynomial_add(poly, polynomial_multiply_constant(temp,coords[i][1]))
    return poly
    
#wrapper for encryption that nicely converts crypto-things to something you can encrypt
def encrypt(key, plaintext):
    key_bytes = hashlib.sha256(pickle.dumps(key)).digest()
    encryptor = AES.new(key_bytes[:32], AES.MODE_CBC, 'This is an IV456')
    plaintext_bytes = pickle.dumps(plaintext)
    #seriously, why do I have to do the padding...
    #TODO: test that this padding is okay in more cases
    while len(plaintext_bytes) %16 != 0:
        plaintext_bytes = plaintext_bytes + b'\x00'
    return encryptor.encrypt(plaintext_bytes)
    
def decrypt(key, ciphertext):
        key_bytes = hashlib.sha256(pickle.dumps(key)).digest()
        decryptor = AES.new(key_bytes[:32], AES.MODE_CBC, 'This is an IV456')
        plaintext_bytes = decryptor.decrypt(ciphertext)
        #now we need to strip the padding off the end
        #if it's stupid but it works...
        #elementsize = len(pickle.dumps(ZR.rand()))
        #paddingsize = (16 -elementsize%16)%16
        return pickle.loads(plaintext_bytes)

##### Hereafter be ZK Proofs ############

### NIZK that two group elements are raised to the same exponent ###
#Let g1=e1^exp and g2=e2^exp. Generate a ZK proof that 
#g1 and g2 are the result of raising e1 and e2 to the same exponent
def prove_same_exponent(e1,e2,exp):
    blind = ZR.rand()
    k1 = e1 ** blind
    k2 = e2 ** blind
    challenge = ZR(int(hashlib.sha256(pickle.dumps(k1) + pickle.dumps(k2)).hexdigest(),16))
    s = blind - challenge*exp
    return [k1, k2, s]

#"proof" is a list of the form [k1, k2, challenge, s]
def check_same_exponent_proof(proof, e1, e2, g1, g2):
    challenge = ZR(int(hashlib.sha256(pickle.dumps(proof[0]) + pickle.dumps(proof[1])).hexdigest(),16))
    eq1 = str(proof[0]) == str(e1 ** proof[2] * g1 ** challenge)
    eq2 = str(proof[1]) == str(e2 ** proof[2] * g2 ** challenge)
    return eq1 and eq2
