"""
019_packet_parser.py - framing a byte stream into packets (lecture 019).

Packet format (one packet):
    [0xAA] [LEN] [DATA_0 ... DATA_(LEN-1)] [CHK]
      HEADER  1 byte, always 0xAA
      LEN     1 byte, number of data bytes, 0..255
      DATA    LEN bytes, anything (may even contain 0xAA)
      CHK     1 byte = (LEN + sum(DATA)) % 256

Bytes arrive in chunks of any size via feed(chunk). Bytes outside a packet (noise, e.g. 0x00)
are skipped. A packet may be split across chunks; a chunk may hold several packets.
A packet whose checksum is wrong is dropped. get_all_packets() returns every valid payload
completed so far (as bytes) and clears that list.

Two implementations with the same interface:
  StateMachineParser   - one byte at a time, explicit states (no buffering of the whole stream)
  ResyncingParser      - buffer-based; on a bad checksum it rescans from the byte after the
                         false header, so a real packet hidden inside a corrupt one is not lost
"""

HEADER = 0xAA


def checksum(length, data):
    """What CHK must equal: the low 8 bits of LEN + every data byte."""
    return (length + sum(data)) % 256


class StateMachineParser:
    # The four states. Each name says what the NEXT byte is expected to be.
    WAIT_HEADER, READ_LENGTH, READ_DATA, READ_CHECKSUM = range(4)

    def __init__(self):
        self.state = self.WAIT_HEADER
        self.length = 0            # LEN of the packet being read (valid set: 0..255)
        self.data = bytearray()    # data bytes collected so far (0..length of them)
        self.completed = []        # valid payloads not yet handed out
        self.dropped = 0           # packets thrown away for a bad checksum

    def feed(self, chunk):
        for byte in chunk:         # iterating over bytes gives ints 0..255
            self._step(byte)

    def _step(self, byte):
        """One step: (state, byte) -> next state. Every state handles every byte."""
        if self.state == self.WAIT_HEADER:
            if byte == HEADER:
                self.state = self.READ_LENGTH
            # any other byte is noise: stay in WAIT_HEADER

        elif self.state == self.READ_LENGTH:
            self.length = byte
            self.data = bytearray()
            # LEN = 0 means "no data": go straight to the checksum
            self.state = self.READ_CHECKSUM if self.length == 0 else self.READ_DATA

        elif self.state == self.READ_DATA:
            self.data.append(byte)             # 0xAA here is DATA, not a header
            if len(self.data) == self.length:  # collected exactly LEN bytes
                self.state = self.READ_CHECKSUM

        elif self.state == self.READ_CHECKSUM:
            if byte == checksum(self.length, self.data):
                self.completed.append(bytes(self.data))
            else:
                self.dropped += 1
            self.state = self.WAIT_HEADER      # either way, look for the next packet

    def get_all_packets(self):
        out, self.completed = self.completed, []
        return out


class ResyncingParser:
    """Keeps unconsumed bytes in a buffer; parses whole packets when enough bytes are present."""

    def __init__(self):
        self.buf = bytearray()
        self.completed = []
        self.dropped = 0

    def feed(self, chunk):
        self.buf.extend(chunk)
        self._parse()

    def _parse(self):
        while True:
            start = self.buf.find(HEADER)          # position of the next candidate header
            if start == -1:
                self.buf.clear()                   # all noise: nothing worth keeping
                return
            del self.buf[:start]                   # drop the noise before it; header now at 0
            if len(self.buf) < 2:
                return                             # need LEN before we know the size
            length = self.buf[1]
            total = 1 + 1 + length + 1             # header + LEN + data + CHK
            if len(self.buf) < total:
                return                             # packet not complete yet: wait for more bytes
            data = self.buf[2:2 + length]
            if self.buf[2 + length] == checksum(length, data):
                self.completed.append(bytes(data))
                del self.buf[:total]               # consume the whole packet
            else:
                self.dropped += 1
                del self.buf[:1]                   # NOT the whole thing: drop only the false header
                                                   # and rescan from the very next byte

    def get_all_packets(self):
        out, self.completed = self.completed, []
        return out


# ---------------------------------------------------------------- tests
def make_packet(data):
    data = bytes(data)
    return bytes([HEADER, len(data)]) + data + bytes([checksum(len(data), data)])


def run_tests(cls):
    name = cls.__name__
    p1, p2, p3 = make_packet([0x01, 0x02, 0x03]), make_packet([0xAA, 0x10]), make_packet([])

    # 1. leading noise, then one packet, all in one chunk
    p = cls(); p.feed(bytes([0x00, 0x00]) + p1)
    assert p.get_all_packets() == [bytes([1, 2, 3])], name + " #1"

    # 2. several packets in one chunk, with noise between them; 0xAA inside data; LEN = 0
    p = cls(); p.feed(p1 + b"\x00\x13" + p2 + p3)
    assert p.get_all_packets() == [bytes([1, 2, 3]), bytes([0xAA, 0x10]), b""], name + " #2"

    # 3. one packet split into single-byte chunks (every boundary position)
    p = cls()
    for b in p1:
        p.feed(bytes([b]))
    assert p.get_all_packets() == [bytes([1, 2, 3])], name + " #3"

    # 4. get_all_packets clears: second call returns nothing new
    assert p.get_all_packets() == [], name + " #4"

    # 5. bad checksum is dropped; the next good packet still arrives
    bad = bytearray(p1); bad[-1] ^= 0xFF
    p = cls(); p.feed(bytes(bad) + p2)
    assert p.get_all_packets() == [bytes([0xAA, 0x10])], name + " #5"
    assert p.dropped == 1, name + " #5 dropped"

    # 6. random split points over a long stream
    import random
    random.seed(7)
    payloads = [bytes(random.randrange(256) for _ in range(random.randrange(0, 20))) for _ in range(200)]
    stream = b"".join(b"\x00" * random.randrange(3) + make_packet(d) for d in payloads)
    p = cls(); i = 0
    while i < len(stream):
        n = random.randrange(1, 9)
        p.feed(stream[i:i + n]); i += n
    assert p.get_all_packets() == payloads, name + " #6"
    print(f"{name}: all 6 tests passed")


def hidden_packet_case():
    """A false header followed by a real packet: who recovers it?"""
    # 0xAA, LEN=3, then the real packet starts inside the 'data' of the false one.
    real = make_packet([0x05])                  # AA 01 05 06
    stream = bytes([HEADER, 0x03]) + real       # AA 03 | AA 01 05 06
    for cls in (StateMachineParser, ResyncingParser):
        p = cls(); p.feed(stream)
        print(f"{cls.__name__:20s} -> {p.get_all_packets()}  dropped={p.dropped}")


if __name__ == "__main__":
    run_tests(StateMachineParser)
    run_tests(ResyncingParser)
    hidden_packet_case()
