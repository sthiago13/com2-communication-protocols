"use strict";

const ALLOWED_TYPES = new Set(["MSG", "ACK", "NACK", "ERROR"]);

class FrameError extends Error {}
class ChecksumError extends FrameError {}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
  }
  return ((crc ^ 0xffffffff) >>> 0).toString(16).toUpperCase().padStart(8, "0");
}

function encodeFrame(type, sequence, payload) {
  if (!ALLOWED_TYPES.has(type)) throw new FrameError(`unsupported type: ${type}`);
  if (!Number.isInteger(sequence) || sequence < 0) throw new FrameError("sequence must be a non-negative integer");

  const payloadBytes = Buffer.from(payload, "utf8");
  const header = `V2|${type}|${sequence}|${payloadBytes.length}|${crc32(payloadBytes)}|`;
  return Buffer.concat([Buffer.from(header, "ascii"), payloadBytes]);
}

function decodeFrame(raw) {
  const bytes = Buffer.from(raw);
  const separators = [];
  for (let index = 0; index < bytes.length && separators.length < 5; index += 1) {
    if (bytes[index] === 124) separators.push(index);
  }
  if (separators.length !== 5) throw new FrameError("frame must contain six fields");

  const headerField = (start, end) => bytes.subarray(start, end).toString("ascii");
  const version = headerField(0, separators[0]);
  const type = headerField(separators[0] + 1, separators[1]);
  const sequence = Number(headerField(separators[1] + 1, separators[2]));
  const declaredLength = Number(headerField(separators[2] + 1, separators[3]));
  const declaredCrc = headerField(separators[3] + 1, separators[4]).toUpperCase();
  const payloadBytes = bytes.subarray(separators[4] + 1);

  if (version !== "V2") throw new FrameError(`unsupported version: ${version}`);
  if (!ALLOWED_TYPES.has(type)) throw new FrameError(`unsupported type: ${type}`);
  if (!Number.isInteger(sequence) || sequence < 0 || !Number.isInteger(declaredLength) || declaredLength < 0) {
    throw new FrameError("sequence and length must be non-negative integers");
  }
  if (!/^[0-9A-F]{8}$/.test(declaredCrc)) throw new FrameError("CRC32 must contain eight hexadecimal characters");
  if (payloadBytes.length !== declaredLength) throw new FrameError("declared payload length does not match datagram");
  if (crc32(payloadBytes) !== declaredCrc) throw new ChecksumError("payload CRC32 mismatch");

  return { version, type, sequence, payload: payloadBytes.toString("utf8") };
}

module.exports = { ChecksumError, FrameError, crc32, decodeFrame, encodeFrame };
