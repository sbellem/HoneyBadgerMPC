ARG HBMPC_DEPS_DIGEST="46902d869ea881d7b00b72ff6accf2558a5e15849da5fa5cc722b4ff82a507f8"

FROM initc3/honeybadgermpc-deps@sha256:$HBMPC_DEPS_DIGEST AS build-compute-power-sums
COPY apps/asynchromix/cpp/ /usr/src/apps/asynchromix/cpp/
RUN make -C /usr/src/apps/asynchromix/cpp

FROM initc3/honeybadgermpc-deps@sha256:$HBMPC_DEPS_DIGEST as base

RUN pip install --upgrade pip
COPY pairing /usr/src/pairing
RUN pip install -v /usr/src/pairing/

ENV HBMPC_HOME /usr/src/HoneyBadgerMPC
WORKDIR $HBMPC_HOME
COPY --from=build-compute-power-sums /usr/local/bin/compute-power-sums /usr/local/bin/

# default location for logs, such as benchmark logs
RUN mkdir -p /var/log/hbmpc

# solidity
COPY --from=ethereum/solc:0.4.24 /usr/bin/solc /usr/bin/solc

# Bash commands
RUN echo "alias cls=\"clear && printf '\e[3J'\"" >> ~/.bashrc

# Make sh point to bash
# This is being changed since it will avoid any errors in the `launch_mpc.sh` script
# which relies on certain code that doesn't work in container's default shell.
RUN ln -sf bash /bin/sh

# If you're testing out apt dependencies, put them here
RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux \
    vim

# Install remaining pip dependencies here
COPY setup.py .
COPY setup.cfg .
COPY apps ./apps
COPY honeybadgermpc ./honeybadgermpc
RUN pip install -e .['dev']


# MP-SPDZ
FROM buildpack-deps:buster as MP-SPDZ-builder
ENV MP_SPDZ_HOME /usr/src/MP-SPDZ
RUN apt-get update && apt-get install -y --no-install-recommends \
                automake \
                build-essential \
                git \
                libboost-dev \
                libboost-thread-dev \
                libsodium-dev \
                libssl-dev \
                libtool \
                m4 \
                texinfo \
                yasm \
                vim \
                gdb \
                valgrind \
        && rm -rf /var/lib/apt/lists/*

WORKDIR $MP_SPDZ_HOME

# mpir
RUN mkdir -p /usr/local/share/info
COPY --from=initc3/mpir:55fe6a9 /usr/local/mpir/lib/* /usr/local/lib/
COPY --from=initc3/mpir:55fe6a9 /usr/local/mpir/include/* /usr/local/include/
COPY --from=initc3/mpir:55fe6a9 /usr/local/mpir/share/info/* /usr/local/share/info/

# DEBUG flags
RUN echo "MY_CFLAGS += -DDEBUG_NETWORKING" >> CONFIG.mine \
        && echo "MY_CFLAGS += -DVERBOSE" >> CONFIG.mine \
        && echo "MY_CFLAGS += -DDEBUG_MAC" >> CONFIG.mine \
        && echo "MY_CFLAGS += -DDEBUG_FILE" >> CONFIG.mine
        #&& echo "MY_CFLAGS += -DDEBUG_MATH" >> CONFIG.mine
RUN echo "MOD = -DGFP_MOD_SZ=4" >> CONFIG.mine

COPY MP-SPDZ .

RUN make random-shamir.x


FROM base
RUN apt-get update && apt-get install -y --no-install-recommends \
                libboost-dev \
                libboost-thread-dev \
                libsodium-dev
# mpir
RUN mkdir -p /usr/local/share/info
COPY --from=initc3/mpir:55fe6a9 /usr/local/mpir/lib/* /usr/local/lib/
COPY --from=initc3/mpir:55fe6a9 /usr/local/mpir/include/* /usr/local/include/
COPY --from=initc3/mpir:55fe6a9 /usr/local/mpir/share/info/* /usr/local/share/info/

# MP-SPDZ
COPY --from=MP-SPDZ-builder /usr/src/MP-SPDZ/random-shamir.x $HBMPC_HOME/apps/inputmasks/

COPY MP-SPDZ /usr/src/MP-SPDZ

WORKDIR $HBMPC_HOME/apps/inputmasks

# FIXME remove this, as it is a setup phase, and in a real deployment keys
# would not be shared
#RUN mkdir -p ./Player-Data \
        #&& bash /usr/src/MP-SPDZ/Scripts/setup-ssl.sh 4
