const test = require("node:test");
const assert = require("node:assert/strict");

const { decodeFrame, encodeFrame } = require("./protocol_v1");

test("encodes and decodes a v1 response", () => {
  const raw = encodeFrame("RESPONSE", 7, "RECIBIDO: hola|mundo");

  assert.deepEqual(decodeFrame(raw), {
    version: "V1",
    type: "RESPONSE",
    sequence: 7,
    payload: "RECIBIDO: hola|mundo",
  });
});

test("rejects a frame with a wrong byte length", () => {
  assert.throws(() => decodeFrame(Buffer.from("V1|RESPONSE|7|99|hola")));
});
