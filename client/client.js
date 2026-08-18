#!/usr/bin/env node
"use strict";

const dgram = require("node:dgram");
const { decodeFrame, encodeFrame } = require("./protocol_v1");

function parseArgs(argv) {
  const options = { host: "127.0.0.1", port: 9000, timeoutMs: 1500, sequence: 1, message: null };
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!value || !["--host", "--port", "--timeout-ms", "--sequence", "--message"].includes(key)) {
      throw new Error("usage: node client/client.js --message TEXT [--host HOST --port PORT --sequence N --timeout-ms N]");
    }
    if (key === "--host") options.host = value;
    if (key === "--port") options.port = Number(value);
    if (key === "--timeout-ms") options.timeoutMs = Number(value);
    if (key === "--sequence") options.sequence = Number(value);
    if (key === "--message") options.message = value;
  }
  if (!options.message || !Number.isInteger(options.port) || !Number.isInteger(options.timeoutMs) || !Number.isInteger(options.sequence)) {
    throw new Error("message, port, timeout and sequence must be valid");
  }
  return options;
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`[client] ${error.message}`);
    process.exitCode = 2;
    return;
  }

  const socket = dgram.createSocket("udp4");
  const request = encodeFrame("MSG", options.sequence, options.message);
  const timer = setTimeout(() => {
    console.error(`[client] TIMEOUT: no response for seq=${options.sequence} after ${options.timeoutMs} ms`);
    socket.close();
    process.exitCode = 1;
  }, options.timeoutMs);

  socket.on("message", (raw, remote) => {
    clearTimeout(timer);
    try {
      const frame = decodeFrame(raw);
      console.log(`[client] received from ${remote.address}:${remote.port} seq=${frame.sequence} payload=${frame.payload}`);
      process.exitCode = frame.type === "RESPONSE" ? 0 : 1;
    } catch (error) {
      console.error(`[client] invalid response: ${error.message}`);
      process.exitCode = 1;
    } finally {
      socket.close();
    }
  });

  socket.send(request, options.port, options.host, (error) => {
    if (error) {
      clearTimeout(timer);
      console.error(`[client] send failed: ${error.message}`);
      socket.close();
      process.exitCode = 1;
      return;
    }
    console.log(`[client] sent seq=${options.sequence} to udp://${options.host}:${options.port}`);
  });
}

main();
