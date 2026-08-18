# Protocolo V2

## Objetivo

V2 mantiene el transporte UDP y corrige las debilidades observadas en V1:

- CRC32 detecta cambios en el payload.
- ACK confirma la recepción correcta.
- NACK informa una corrupción recuperable.
- Timeout y retransmisión Stop-and-Wait recuperan mensajes perdidos.
- La caché por secuencia evita procesar duplicados y reutiliza el ACK original.
- Un pool de trabajadores permite procesar solicitudes de varios clientes concurrentemente.
- La caché se protege con exclusión mutua y se identifica por cliente y secuencia.

## Formato de trama

```text
V2|TYPE|SEQUENCE|LENGTH|CRC32|PAYLOAD
```

| Campo | Descripción |
| --- | --- |
| `V2` | Versión robustecida. |
| `TYPE` | `MSG`, `ACK`, `NACK` o `ERROR`. |
| `SEQUENCE` | Identificador entero no negativo. |
| `LENGTH` | Longitud UTF-8 del payload en bytes. |
| `CRC32` | Ocho dígitos hexadecimales calculados sobre el payload. |
| `PAYLOAD` | Contenido de la trama. |

## Flujo Stop-and-Wait

1. El cliente envía un `MSG` y activa un temporizador.
2. El servidor verifica longitud, UTF-8 y CRC32.
3. Si la trama es válida y nueva, la procesa, almacena su ACK y responde.
4. Si el CRC32 es incorrecto, responde `NACK|CRC_MISMATCH` sin procesarla.
5. Si la secuencia ya fue procesada, no repite la operación: reenvía el ACK almacenado.
6. Si una secuencia se reutiliza con otro payload, responde `ERROR|SEQUENCE_CONFLICT` en lugar de devolver un ACK antiguo.
7. Ante NACK o timeout, el cliente retransmite la misma secuencia hasta agotar `--retries`.

> Reinicie servidor y proxy antes de cada escenario para aislar las pruebas. Si decide conservar el servidor activo, use secuencias distintas (`--sequence 1`, `--sequence 2`, `--sequence 3`). Una retransmisión siempre conserva la secuencia original.

## Validación 1: pérdida

```bash
# Terminal 1
python server/server_v2.py --port 9001

# Terminal 2
python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --drop-client-to-server 1

# Terminal 3
node client/client_v2.js --port 9000 --sequence 1 --message "Mensaje perdido" --timeout-ms 500 --retries 3
```

Resultado esperado: primer intento descartado, timeout, segundo intento y ACK. El servidor procesa el mensaje una sola vez.

## Validación 2: corrupción

```bash
# Terminal 1
python server/server_v2.py --port 9001

# Terminal 2
python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --corrupt-client-to-server 1

# Terminal 3
node client/client_v2.js --port 9000 --sequence 2 --message "Hola mundo" --timeout-ms 500 --retries 3
```

Resultado esperado: el servidor rechaza el primer intento por CRC32, envía NACK y procesa solamente la retransmisión intacta.

## Validación 3: duplicación

```bash
# Terminal 1
python server/server_v2.py --port 9001

# Terminal 2
python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --duplicate-client-to-server 1

# Terminal 3
node client/client_v2.js --port 9000 --sequence 3 --message "Pago 100" --timeout-ms 500 --retries 3
```

Resultado esperado: el servidor registra un único `processed` y luego `duplicate ... without processing`. Ambas copias reciben el mismo ACK.

## Evidencia

Para cada escenario capture las tres terminales y Wireshark con:

```text
udp.port == 9000 or udp.port == 9001
```

Ejecute cada falla por separado para conservar la comparación directa con V1.

## Validación de concurrencia

Inicie el servidor directamente con cuatro trabajadores y una demora demostrativa:

```bash
python server/server_v2.py --port 9001 --workers 4 --processing-delay-ms 1000
```

Desde otra terminal Git Bash, inicie dos clientes en segundo plano:

```bash
node client/client_v2.js --port 9001 --sequence 10 --message "Cliente A" --timeout-ms 2000 --retries 1 & node client/client_v2.js --port 9001 --sequence 11 --message "Cliente B" --timeout-ms 2000 --retries 1 & wait
```

El registro debe contener dos eventos `START` de trabajadores distintos antes del primer `END`. Las secuencias se mantienen separadas por cliente y la caché usa un bloqueo para impedir carreras durante la deduplicación.
