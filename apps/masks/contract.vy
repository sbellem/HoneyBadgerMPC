# event PreProcessUpdated();
# NOTE solidity: event InputMaskClaimed(address client, uint inputmask_idx);
event InputMaskClaimed({_client: address, _inputmask_idx: uint256})

# NOTE solidity: event MessageSubmitted(uint idx, uint inputmask_idx, bytes32 masked_input);
event MessageSubmitted({_idx: uint256, _inputmask_idx: uint256, _masked_input: bytes32})

# NOTE solidity: event MpcEpochInitiated(uint epoch);
event MpcEpochInitiated(_epoch: uint256})

# NOTE solidity: event MpcOutput(uint epoch, string output);
# NOTE vyper does not allow dynamic arrays, so we have to set the maximum
# expected length of the output. The output string can contain up through
# the maximum number of characters. Meaning: x = string[100], x can be
# 1 to 100 character long.
event MpcOutput(_epoch: uint256, _output: string[100])

# Session parameters
n: public(uint256)
t: public(uint256)
servers: public(address[100])
servermap: public(map(address, uint256))

# constructor(address[] memory _servers, uint _t) public {
@public
def __init__(_servers: address[100], _n: uint256, _t: uint256):
    assert _n <= 100
    assert 3 * _t < _n
	self.n = _n
	self.t  = _t

	# servers.length = n;
	#for (uint i = 0; i < n; i++) {
	#    servers[i] = _servers[i];
	#    servermap[_servers[i]] = i+1; // servermap is off-by-one
	#}
    for i in range(n):
        self.servers[i] = _servers[i]
        self.servermap[_servers[i]] = i + 1     # servermap is off-by-one
