const test = require("node:test");
const assert = require("node:assert/strict");

const { ChecksumError, decodeFrame, encodeFrame } = require("./protocol_v2");

test("encodes and decodes a V2 ACK", () => {
  const raw = encodeFrame("ACK", 4, "RECIBIDO: acción");

  assert.deepEqual(decodeFrame(raw), {
    version: "V2",
    type: "ACK",
    sequence: 4,
    payload: "RECIBIDO: acción",
  });
});

test("rejects same-length corruption with CRC32", () => {
  const raw = Buffer.from(encodeFrame("MSG", 4, "Hola"));
  raw[raw.length - 1] = "A".charCodeAt(0);

  assert.throws(() => decodeFrame(raw), ChecksumError);
});
