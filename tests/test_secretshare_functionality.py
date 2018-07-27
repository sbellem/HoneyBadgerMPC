import asyncio
import random


async def _test1(sid='sid', N=4, f=1, Dealer=0):
    from honeybadgermpc.secretshare_functionality import (SecretShare_IdealProtocol,
                                                          Poly, Field)
    # Create ideal protocol for all the parties
    SecretShare = SecretShare_IdealProtocol(N,f)
    parties = [SecretShare(sid,Dealer,i) for i in range(N)]

    # Output (promises) are available, but not resolved yet
    for i in range(N):
        print(i, parties[i].output)

    # Show the shared functionality
    print(parties[0]._instances[sid])

    # Provide input
    v = Field(random.randint(0,Field.modulus-1))
    print("Dealer's input:", v)
    parties[Dealer].inputFromDealer.set_result(v)

    # Now can await output from each AVSS protocol
    for i in range(N):
        await parties[i].output
        print(i, parties[i].output)

    # Reconstructed
    rec = Poly.interpolate_at([(i+1,parties[i].output.result()) for i in range(f+1)])
    print("Reconstruction:", rec)
        

def test():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try:
        # Run some test cases
        loop.run_until_complete(_test1())
    finally:
        loop.close()
