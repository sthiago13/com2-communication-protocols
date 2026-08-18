#!/usr/bin/env node
"use strict";

const dgram = require("node:dgram");
const { decodeFrame, encodeFrame } = require("./protocol_v2");

function parseArgs(argv) {
  const options = { host: "127.0.0.1", port: 9000, timeoutMs: 500, sequence: 1, retries: 3, message: null };
  const allowed = new Set(["--host", "--port", "--timeout-ms", "--sequence", "--retries", "--message"]);
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!value || !allowed.has(key)) {
      throw new Error("usage: node client/client_v2.js --message TEXT [--host HOST --port PORT --sequence N --timeout-ms N --retries N]");
    }
    if (key === "--host") options.host = value;
    if (key === "--port") options.port = Number(value);
    if (key === "--timeout-ms") options.timeoutMs = Number(value);
    if (key === "--sequence") options.sequence = Number(value);
    if (key === "--retries") options.retries = Number(value);
    if (key === "--message") options.message = value;
  }
  const numbers = [options.port, options.timeoutMs, options.sequence, options.retries];
  if (!options.message || numbers.some((value) => !Number.isInteger(value) || value < 0) || options.timeoutMs === 0) {
    throw new Error("message and non-negative integer parameters are required");
  }
  return options;
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`[client-v2] ${error.message}`);
    process.exitCode = 2;
    return;
  }

  const socket = dgram.createSocket("udp4");
  const request = encodeFrame("MSG", options.sequence, options.message);
  let attempts = 0;
  let timer = null;
  let finished = false;

  function finish(exitCode) {
    if (finished) return;
    finished = true;
    if (timer) clearTimeout(timer);
    process.exitCode = exitCode;
    socket.close();
  }

  function sendAttempt(reason) {
    if (finished) return;
    attempts += 1;
    socket.send(request, options.port, options.host, (error) => {
      if (error) {
        console.error(`[client-v2] send failed: ${error.message}`);
        finish(1);
        return;
      }
      console.log(`[client-v2] sent seq=${options.sequence} attempt=${attempts} reason=${reason}`);
    });
    timer = setTimeout(() => {
      if (attempts <= options.retries) {
        console.log(`[client-v2] timeout seq=${options.sequence}; retransmitting`);
        sendAttempt("timeout");
      } else {
        console.error(`[client-v2] FAILED seq=${options.sequence} after ${attempts} attempts`);
        finish(1);
      }
    }, options.timeoutMs);
  }

  socket.on("message", (raw) => {
    let frame;
    try {
      frame = decodeFrame(raw);
    } catch (error) {
      console.error(`[client-v2] discarded invalid response: ${error.message}`);
      return;
    }
    if (frame.sequence !== options.sequence) {
      console.log(`[client-v2] ignored response for seq=${frame.sequence}`);
      return;
    }
    if (timer) clearTimeout(timer);
    if (frame.type === "ACK") {
      console.log(`[client-v2] ACK seq=${frame.sequence} attempts=${attempts} payload=${frame.payload}`);
      finish(0);
      return;
    }
    if (frame.type === "NACK" && attempts <= options.retries) {
      console.log(`[client-v2] NACK seq=${frame.sequence} reason=${frame.payload}; retransmitting`);
      sendAttempt("NACK");
      return;
    }
    console.error(`[client-v2] server error type=${frame.type} payload=${frame.payload}`);
    finish(1);
  });

  sendAttempt("initial");
}

main();
