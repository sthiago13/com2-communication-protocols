"use strict";

const ALLOWED_TYPES = new Set(["MSG", "RESPONSE", "ERROR"]);

function encodeFrame(type, sequence, payload) {
  if (!ALLOWED_TYPES.has(type)) throw new Error(`unsupported type: ${type}`);
  if (!Number.isInteger(sequence) || sequence < 0) throw new Error("sequence must be a non-negative integer");

  const payloadBytes = Buffer.from(payload, "utf8");
  return Buffer.concat([Buffer.from(`V1|${type}|${sequence}|${payloadBytes.length}|`, "ascii"), payloadBytes]);
}

function decodeFrame(raw) {
  const bytes = Buffer.from(raw);
  const separators = [];
  for (let index = 0; index < bytes.length && separators.length < 4; index += 1) {
    if (bytes[index] === 124) separators.push(index);
  }
  if (separators.length !== 4) throw new Error("frame must contain five fields");

  const version = bytes.subarray(0, separators[0]).toString("ascii");
  const type = bytes.subarray(separators[0] + 1, separators[1]).toString("ascii");
  const sequence = Number(bytes.subarray(separators[1] + 1, separators[2]).toString("ascii"));
  const declaredLength = Number(bytes.subarray(separators[2] + 1, separators[3]).toString("ascii"));
  const payloadBytes = bytes.subarray(separators[3] + 1);

  if (version !== "V1") throw new Error(`unsupported version: ${version}`);
  if (!ALLOWED_TYPES.has(type)) throw new Error(`unsupported type: ${type}`);
  if (!Number.isInteger(sequence) || sequence < 0 || !Number.isInteger(declaredLength) || declaredLength < 0) {
    throw new Error("sequence and length must be non-negative integers");
  }
  if (payloadBytes.length !== declaredLength) throw new Error("declared payload length does not match datagram");

  return { version, type, sequence, payload: payloadBytes.toString("utf8") };
}

module.exports = { decodeFrame, encodeFrame };
