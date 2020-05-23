# event PreProcessUpdated();
InputMaskClaimed: event({_client: address, _inputmask_idx: uint256})
MessageSubmitted: event({_idx: uint256, _inputmask_idx: uint256, _masked_input: bytes32})
MpcEpochInitiated: event({_epoch: uint256})

# NOTE vyper does not allow dynamic arrays, so we have to set the maximum
# expected length of the output. The output string can contain up through
# the maximum number of characters. Meaning: x = string[100], x can be
# 1 to 100 character long.
MpcOutput: event({_epoch: uint256, _output: string[100]})

# NOTE: Not sure if there's a way around this ... must
# hardcode number of participants
N: constant(uint256) = 4

# Session parameters
t: public(uint256)
servers: public(address[4])
servermap: public(map(address, int128))

@public
@constant
def n() -> uint256:
    return N


@public
def __init__(_servers: address[N], _t: uint256):
    assert 3 * _t < N
    self.t = _t

    for i in range(N):
        self.servers[i] = _servers[i]
        self.servermap[_servers[i]] = i + 1   # servermap is off-by-one

# TODO
# 1. Preprocessing Buffer (the MPC offline phase)

#struct PreProcessCount {
#    uint inputmasks;     // [r]
#}
#
#// Consensus count (min of the player report counts)
#PreProcessCount public preprocess;
#
#// How many of each have been reserved already
#PreProcessCount public preprocess_used;
#
#function inputmasks_available () public view returns(uint) {
#    return preprocess.inputmasks - preprocess_used.inputmasks;
#}
#
#// Report of preprocess buffer size from each server
#mapping ( uint => PreProcessCount ) public preprocess_reports;
#
#// NOTE not sure if needed, commenting for now
#// event PreProcessUpdated();
#
#function min(uint a, uint b) private pure returns (uint) {
#    return a < b ? a : b;
#}
#
#function max(uint a, uint b) private pure returns (uint) {
#    return a > b ? a : b;
#}
#
#function preprocess_report(uint[1] memory rep) public {
#    // Update the Report 
#    require(servermap[msg.sender] > 0);   // only valid servers
#    uint id = servermap[msg.sender] - 1;
#    preprocess_reports[id].inputmasks = rep[0];
#
#    // Update the consensus
#    // .triples = min (over each id) of _reports[id].triples; same for bits, etc. 
#    PreProcessCount memory mins;
#    mins.inputmasks = preprocess_reports[0].inputmasks;
#    for (uint i = 1; i < n; i++) {
#        mins.inputmasks = min(mins.inputmasks, preprocess_reports[i].inputmasks);
#    }
#    // NOTE not sure if needed, commenting for now
#    // if (preprocess.inputmasks < mins.inputmasks) {
#    //     emit PreProcessUpdated();
#    // }
#    preprocess.inputmasks = mins.inputmasks;
#}
