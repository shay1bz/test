from typing import Set

"""
Design choices:
    - using python for rapid development. In real world scenario I would use Java (as I don't have experience with c/c++) for better security
    - the implementation is not secured - largely due to python nature - users can bypass anything and mess with the underlying data.
    - MemoryManager is the main class that exposes the alloc(size) method, which returns MemoryChunk instance (see below)
    - data access is abstracted behind MemoryChunk, which exposes free, read and write methods
    - this implementation is NOT thread safe due to time constraints
    - whenever memory cannot be allocated due to fragmentation, de-frag process will initiate
    - the implementation is not robust - intermediate failures might (and will) leave the manager in corrupted state. 
        This could be handled with some simple try/catch blocks at the right places. 
    - the defrag implementation is naive due to time constraints. A more advanced approaches would split the buffer 
        into segments - for example 2 sub buffers for big/large allocations, use greedy algorithm to make room for 
        the new alloc instead of de-fragging the entire buffer, use advanced data structures, etc.


High level description of the implementation:
    The manager's state contains these main variables:
    - _buf: the backbone bytebuffer
    - _free_bytes: num of free bytes - simply for fast-checking of available space on alloc() request
    - _allocated_chunks: set of *active* (not-freed) MemoryChunks, to validate 
    - _free_slots: array of tuples - (offset, size) - representing sequences of available memory slots in the buffer
    
    Upon calling alloc(), we first make sure there is enough space in the buffer (globally). Then we check if we can 
        find it inside on of the available slots. If not, we run a de-frag process on the entire buffer.
    The MemoryChunk class a simple - almost pojo - wrapper around the offset and size specs. It offloads any function
        to the manager itself.
      
     

"""


class MemoryChunk:
    def __init__(self, offset, size, manager):
        self._offset = offset
        self._size = size
        self.manager = manager

    def free(self):
        self.manager.free(self)

    def read(self, start=0, size=None):
        return self.manager.read(self, start, size)

    def write(self, data: str | bytearray, start=0):
        self.manager.write(self, data, start)


class MemoryManager:

    def __init__(self, size_bytes):
        self._buf = bytearray(size_bytes)
        self._size = size_bytes
        self._free_bytes = size_bytes
        self._allocated_chunks: Set[MemoryChunk] = set()
        self._free_slots = [(0, size_bytes)]

    def alloc(self, size) -> MemoryChunk:

        if size > self._free_bytes:
            raise MemoryAllocationError("Not enough free space available")

        def do_alloc():
            for i, (slot_offset, slot_size) in enumerate(self._free_slots):
                if size <= slot_size:
                    res = MemoryChunk(slot_offset, size, self)
                    if size == slot_size:
                        self._free_slots.pop(i)
                    else:
                        self._free_slots[i] = (slot_offset + size, slot_size - size)
                    self._allocated_chunks.add(res)
                    self._free_bytes -= size
                    self._buf[slot_offset: slot_offset + size] = bytearray(size)
                    return res

        res = do_alloc()
        if res is None:
            # if got here, we need to de-frag
            self._defrag()
            res = do_alloc()
        assert res, "INTERNAL ERROR!"

        return res

    def read(self, chunk: MemoryChunk, start, size):
        assert start >= 0
        start = chunk._offset + start
        size = size or chunk._size

        assert self.is_valid(chunk), "Unrecognized memory chunk!"
        assert size <= chunk._size, "Out of memory boundaries"
        return self._buf[start:start + size]

    def write(self, chunk: MemoryChunk, data: str | bytearray, start=0):
        assert self.is_valid(chunk), "Unrecognized memory chunk!"
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif isinstance(data, bytes):
            pass
        else:
            raise RuntimeError("Data must be string or bytearray!")

        end = start + len(data)
        assert end <= chunk._size, "Out of memory boundaries"
        assert start >= 0

        buffer: bytearray = self._buf
        buffer[chunk._offset + start: end] = data

    def is_valid(self, chunk: MemoryChunk):
        return chunk in self._allocated_chunks

    def free(self, chunk: MemoryChunk):
        if chunk not in self._allocated_chunks:
            raise RuntimeError("Unknown MemoryChunk!")
        self._allocated_chunks.remove(chunk)
        self._free_slots.append((chunk._offset, chunk._size))
        self._free_bytes += chunk._size

    def _defrag(self):
        """ de-frags the buffer, by simply offsetting all the used chunks to the left side, 
        creating one consecutive allocated-chunks, starts with 0 index."""

        # sorting the chunks by offset, relying on naive heuristic that if the first chunks were not freed, 
        # we can leave them in place and spare the copying.
        sorted_chunks: [MemoryChunk] = sorted(self._allocated_chunks, key=lambda x: x._offset)

        next_offset = 0
        for chunk in sorted_chunks:
            if chunk._offset != next_offset:
                # move the chunk data inside the buffer to the lowest available offset
                self._buf[next_offset:next_offset + chunk._size] = self._buf[chunk._offset:chunk._offset + chunk._size]
                # update the chunk pointer:
                chunk._offset = next_offset
            next_offset += chunk._size
        assert next_offset == self._size - self._free_bytes, "INTERNAL ERROR"  # sanity check

        # update free list:
        self._free_slots = []
        if self._free_bytes < self._size:
            self._free_slots.append((next_offset, self._size - next_offset))


class MemoryAllocationError(Exception):
    pass
