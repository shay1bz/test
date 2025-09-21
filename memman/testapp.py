import unittest
from memman.app import *


class TestApp(unittest.TestCase):
    def test_sanity(self):
        manager = MemoryManager(100)
        mem = manager.alloc(10)
        # simple:
        mem.write("hello!")
        self.assertEqual(mem.read(0, 6).decode("utf-8"), "hello!")
        # exact match:
        mem.write("1234567890")
        self.assertEqual(mem.read(0).decode("utf-8"), "1234567890")
        self.assertEqual(mem.read(0, 10).decode("utf-8"), "1234567890")

        # negative tests:
        with self.assertRaises(AssertionError):
            mem.write("hello world!!!")
        with self.assertRaises(AssertionError):
            mem.read(0, 30)
        with self.assertRaises(AssertionError):
            mem.read(-2, 30)
        with self.assertRaises(MemoryAllocationError):
            manager.alloc(100)

        mem.free()
        m1 = manager.alloc(3)
        m2 = manager.alloc(3)
        m3 = manager.alloc(3)
        m1.write("abc")
        m2.write("xyz")
        m3.write("qwe")
        self.assertEqual(m1.read(0, 3).decode("utf-8"), "abc")
        self.assertEqual(m2.read(0, 3).decode("utf-8"), "xyz")
        self.assertEqual(m3.read(0, 3).decode("utf-8"), "qwe")

    def test_free(self):
        manager = MemoryManager(10)
        manager.alloc(9).free()

        mem = manager.alloc(9)  # should pass
        mem.write("test")

        with self.assertRaises(MemoryAllocationError):
            manager.alloc(2)
        onebyte = manager.alloc(1)  # should pass
        self.assertEqual(mem.read(0, 4).decode("utf-8"), "test")
        onebyte.write("X")
        self.assertEqual(onebyte.read(0).decode("utf-8"), "X")

    def test_frag(self):
        manager = MemoryManager(10)
        m1 = manager.alloc(3)
        m2 = manager.alloc(3)
        m3 = manager.alloc(3)
        # one byte is free
        m2.free()  # now 4 bytes are free, but fragmented

        # write some data to make sure defrag did not ruin it:
        m1.write("abc")
        m3.write("xyz")

        mem = manager.alloc(4)  # should work and do defrag

        # make sure the data stays the same after defrag:
        self.assertEqual(m1.read(0, 3).decode("utf-8"), "abc")
        self.assertEqual(m3.read(0, 3).decode("utf-8"), "xyz")

        mem.write("test")
        self.assertEqual(mem.read(0, 4).decode("utf-8"), "test")

        # reuse m1:
        m1.write("ABC")
        self.assertEqual(m1.read(0, 3).decode("utf-8"), "ABC")

