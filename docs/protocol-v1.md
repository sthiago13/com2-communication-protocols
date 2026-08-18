# Protocolo V1

## Propósito

V1 establece una comunicación UDP básica entre un cliente Node.js y un servidor Python. Está diseñada como línea base deliberadamente vulnerable: no implementa ACK, retransmisiones, CRC ni control de duplicados.

El servidor recibe datagramas en un bucle principal y delega su procesamiento a un pool de trabajadores. De este modo puede atender solicitudes de distintos clientes de forma concurrente, aunque V1 conserva deliberadamente sus debilidades de confiabilidad.

## Formato de trama

Cada datagrama contiene bytes UTF-8 con cinco campos:

```text
V1|TYPE|SEQUENCE|LENGTH|PAYLOAD
```

| Campo | Descripción |
| --- | --- |
| `V1` | Versión fija del protocolo. |
| `TYPE` | `MSG`, `RESPONSE` o `ERROR`. |
| `SEQUENCE` | Entero no negativo que identifica el mensaje. |
| `LENGTH` | Cantidad de bytes UTF-8 del payload. |
| `PAYLOAD` | Contenido del mensaje. Puede incluir el carácter `|`. |

Ejemplo:

```text
V1|MSG|1|4|Hola
```

El servidor procesa únicamente `MSG` y responde con el mismo número de secuencia:

```text
V1|RESPONSE|1|14|RECIBIDO: Hola
```

## Ataque 1: pérdida de paquetes

### Objetivo

Demostrar que un único datagrama perdido rompe la comunicación en V1 porque el cliente no recibe respuesta y no reintenta el envío.

### Preparación

Abra tres terminales en la raíz del repositorio y deje visible su salida. Opcionalmente inicie Wireshark y capture la interfaz de loopback, filtrando por `udp.port == 9000 or udp.port == 9001`.

### Ejecución

1. Inicie el servidor:

   ```bash
   python server/server.py --port 9001
   ```

2. Inicie el proxy de adversidad para escuchar en el puerto 9000 y descartar exactamente el primer datagrama que llegue desde el cliente:

   ```bash
   python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --drop-client-to-server 1
   ```

3. Ejecute el cliente dirigido al proxy, no al servidor:

   ```bash
   node client/client.js --port 9000 --message "Prueba de pérdida" --timeout-ms 1500
   ```

4. Conserve estas evidencias:
   - consola del proxy: `DROPPED client datagram`;
   - consola del cliente: `TIMEOUT`;
   - consola del servidor: no aparece `received` para esa secuencia;
   - captura Wireshark: existe el datagrama cliente -> proxy (puerto 9000), pero no existe proxy -> servidor (puerto 9001).

5. Registre el resultado en la matriz del informe:

| Falla | Comportamiento de V1 | Evidencia | Solución de V2 |
| --- | --- | --- | --- |
| Pérdida del primer datagrama | El cliente alcanza el timeout; el servidor no procesa el mensaje. | Salida de cliente, proxy y Wireshark. | ACK numerado, timeout y retransmisión Stop-and-Wait. |

### Control experimental

Antes del ataque, ejecute el proxy sin `--drop-client-to-server`. El cliente debe recibir una respuesta. Esa comparación permite atribuir el timeout a la falla inyectada, no a una configuración incorrecta.

## Concurrencia del servidor

El parámetro `--workers` define el tamaño del pool de hilos. Para hacer visible el solapamiento durante una demostración se admite `--processing-delay-ms`; esta demora no forma parte del protocolo ni se utiliza en operación normal.

```bash
python server/server.py --port 9001 --workers 4 --processing-delay-ms 1000
```

Dos clientes pueden iniciarse desde otra terminal con `&` y sincronizarse con `wait`. La evidencia válida presenta dos eventos `START` antes del primer `END`.

## Ataque 2: corrupción de datos

### Objetivo

Demostrar que V1 acepta un payload modificado en tránsito porque su campo `LENGTH` comprueba el tamaño, no la integridad de los bytes.

### Ejecución

1. Inicie el servidor:

   ```bash
   python server/server.py --port 9001
   ```

2. Inicie el proxy con una corrupción determinista del primer datagrama cliente -> servidor:

   ```bash
   python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --corrupt-client-to-server 1
   ```

3. Envíe un mensaje con letras ASCII para que la alteración sea visible:

   ```bash
   node client/client.js --port 9000 --message "Hola mundo" --timeout-ms 1500
   ```

4. Conserve estas evidencias:
   - consola del proxy: `CORRUPTED client datagram`;
   - consola del servidor: `received` con un payload distinto al enviado;
   - consola del cliente: recibe una respuesta exitosa que contiene el texto alterado;
   - captura Wireshark: el datagrama proxy -> servidor muestra el byte alterado respecto al cliente -> proxy.

| Falla | Comportamiento de V1 | Evidencia | Solución de V2 |
| --- | --- | --- | --- |
| Corrupción de un byte del payload | El servidor acepta y responde datos alterados porque el tamaño sigue siendo válido. | Salidas de cliente, proxy, servidor y Wireshark. | CRC32 o checksum verificado antes de procesar la trama. |

## Ataque 3: duplicación de mensajes

### Objetivo

Demostrar que V1 procesa dos veces la misma trama porque no registra secuencias ya procesadas ni hace sus respuestas idempotentes.

### Ejecución

1. Inicie el servidor:

   ```bash
   python server/server.py --port 9001
   ```

2. Inicie el proxy para duplicar exactamente el primer datagrama cliente -> servidor:

   ```bash
   python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --duplicate-client-to-server 1
   ```

3. Envíe un mensaje cuyo procesamiento duplicado sea fácil de explicar. Para la demostración use un texto; en un sistema real podría representar un pago u orden repetida:

   ```bash
   node client/client.js --port 9000 --message "Pago 100" --timeout-ms 1500
   ```

4. Conserve estas evidencias:
   - consola del proxy: `DUPLICATED client datagram`;
   - consola del servidor: dos líneas `received` con el mismo `seq=1` y payload;
   - consola del cliente: recibe al menos una respuesta exitosa;
   - captura Wireshark: dos datagramas idénticos proxy -> servidor.

| Falla | Comportamiento de V1 | Evidencia | Solución de V2 |
| --- | --- | --- | --- |
| Duplicación de un mensaje | El servidor procesa dos veces el mismo número de secuencia. | Dos registros del servidor, salida del proxy y Wireshark. | ACK numerado y registro/caché de secuencias procesadas. |
