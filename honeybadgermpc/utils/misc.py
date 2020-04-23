import asyncio
import logging
import traceback
from asyncio import Queue
from collections import defaultdict
from functools import partial
from typing import Callable

from .typecheck import TypeCheck


def print_exception_callback(future):
    if future.done():
        ex = future.exception()
        if ex is not None:
            tb = "".join(traceback.format_exception(None, ex, ex.__traceback__))
            logging.critical(f"\nException: \n{future} \n{tb})")
            raise ex


@TypeCheck()
def wrap_send(tag: str, send: Callable):  # noqa: F821
    """Given a `send` function which takes a destination and message,
    this returns a modified function which sends the tag with the object.
    """

    def _send(dest, message):
        logging.debug(f"sending to: {dest}, tag: {tag}, message {message}")
        send(dest, (tag, message))

    return _send


@TypeCheck()
def chunk_data(data: list, chunk_size: int, default: int = 0):
    """ Break data into chunks of size `chunk_size`
    Last chunk is padded with the default value to have `chunk_size` length
    If an empty list is provided, this will return a single chunk of default values
    e.g. chunk_data([1,2,3,4,5], 2) => [[1,2], [3,4], [5, 0]]
         chunk_data([], 2) => [[0, 0]]
    """
    if len(data) == 0:
        return [default] * chunk_size

    # Main chunking
    res = [
        data[start : (start + chunk_size)] for start in range(0, len(data), chunk_size)
    ]

    # Pad final chunk with default value
    res[-1] += [default] * (chunk_size - len(res[-1]))

    return res


@TypeCheck()
def flatten_lists(lists: list):
    """ Given a 2d list, return a flattened 1d list
    e.g. [[1,2,3],[4,5,6],[7,8,9]] => [1,2,3,4,5,6,7,8,9]
    """
    res = []
    for inner in lists:
        res += inner

    return res


@TypeCheck()
def transpose_lists(lists: list):
    """ Given a 2d list, return the transpose of the list
    e.g. [[1,2,3],[4,5,6],[7,8,9]] => [[1,4,7],[2,5,8],[3,6,9]]
    """
    rows = len(lists)
    cols = len(lists[0])
    return [[lists[j][i] for j in range(rows)] for i in range(cols)]


def subscribe_recv(recv):
    """ Given the recv method for this batch reconstruction,
    create a background loop to put the received events into
    the appropriate queue for the tag

    Returns _task and subscribe, where _task is to be run in
    the background to forward events to the associated queue,
    and subscribe, which is used to register a new tag/queue pair
    """
    # Stores the queues for each subscribed tag
    tag_table = defaultdict(Queue)
    taken = set()  # Replace this with a bloom filter?

    async def _recv_loop():
        while True:
            # Whenever we receive a share array, directly put it in the
            # appropriate queue for that round
            j, (tag, o) = await recv()
            logging.debug(f"received tag: {tag}")
            tag_table[tag].put_nowait((j, o))

    def subscribe(tag):
        # TODO: make this raise an exception
        # Ensure that this tag has not been subscribed to already
        logging.debug(f"subscribing to tag: {tag}")
        assert tag not in taken
        taken.add(tag)

        # Return the getter of the queue for this tag
        return tag_table[tag].get

    _task = asyncio.create_task(_recv_loop())
    return _task, subscribe


def _get_send_recv(tag, *, send, subscribe):
    return wrap_send(tag, send), subscribe(tag)


def _get_pubsub_channel(send, recv):
    sub_task, sub = subscribe_recv(recv)
    return sub_task, partial(_get_send_recv, send=send, subscribe=sub)
