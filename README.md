# com2-communication-protocols

Implementación completa del Parcial III de Comunicaciones II: diseño de un protocolo UDP cliente-servidor, evaluación adversarial de su versión inicial (V1) y robustecimiento en una segunda versión (V2). Los experimentos cubren pérdida, corrupción y duplicación de datagramas.

Repositorio: <https://github.com/sthiago13/com2-communication-protocols>

## Integrantes y responsabilidades

- **Santiago Hernández Gelvez:** lado servidor en Python.
- **José Javier Garcia Peñaloza:** lado cliente CLI en Node.js.
- **Ana Paola Andrade Pineda:** agente de adversidad y apoyo en la captura de tráfico.

El equipo trabajó presencialmente en la residencia de Santiago Hernández Gelvez. Las pruebas finales y la captura consolidada de Wireshark se realizaron en su computador.

## Requisitos

- Python 3.11 o superior (servidor y proxy de adversidad).
- Node.js 20 o superior (cliente).

No se requieren dependencias externas.

## Estructura

```text
server/       Servidores UDP y codecs V1/V2 en Python.
client/       Clientes CLI y codecs V1/V2 en Node.js.
adversary/    Proxy UDP para inyectar pérdida, corrupción y duplicación.
tests/        Pruebas automatizadas del protocolo y el proxy adversario.
docs/         Especificaciones V1/V2 y matriz de errores y soluciones.
output/       Informe técnico editable en formato DOCX.
```

## Ejecutar la comunicación normal

En tres terminales, desde la raíz del repositorio:

```bash
# Terminal 1: servidor real
python server/server.py --port 9001

# Terminal 2: proxy sin pérdida (intermediario del canal)
python adversary/drop_proxy.py --listen-port 9000 --server-port 9001

# Terminal 3: cliente
node client/client.js --port 9000 --message "Hola desde el cliente" --timeout-ms 1500
```

El cliente debe recibir `RECIBIDO: Hola desde el cliente`.

## Primer ataque: pérdida de paquetes

Ejecute el servidor y el cliente como arriba, pero inicie el proxy con una pérdida determinista del primer datagrama:

```bash
python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --drop-client-to-server 1
node client/client.js --port 9000 --message "Mensaje que será perdido" --timeout-ms 1500
```

Resultado esperado de V1: el proxy informa `DROPPED`, el servidor no recibe el mensaje y el cliente termina con `TIMEOUT`. Esto demuestra la debilidad que V2 resolverá con ACK, temporizadores y retransmisión.

Consulte [docs/protocol-v1.md](docs/protocol-v1.md) para el formato exacto y la guía de evidencia.

## Segundo ataque: corrupción de datos

Con el servidor activo, inicie el proxy para alterar una letra del primer payload y luego ejecute el cliente:

```bash
python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --corrupt-client-to-server 1
node client/client.js --port 9000 --message "Hola mundo" --timeout-ms 1500
```

V1 recibirá una respuesta exitosa, pero el servidor habrá procesado el payload alterado. Ese es el fallo: no hay una verificación de integridad que detecte la modificación.

## Tercer ataque: duplicación de mensajes

Con el servidor activo, haga que el proxy reenvíe dos copias del primer mensaje:

```bash
python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --duplicate-client-to-server 1
node client/client.js --port 9000 --message "Pago 100" --timeout-ms 1500
```

El cliente recibirá una respuesta, pero el servidor registrará el mismo `seq=1` dos veces. V1 procesa ambas copias porque no detecta duplicados.

## Pruebas automatizadas

```bash
python -m unittest discover -s tests -p "test_*.py"
node --test client/test_protocol_v1.js client/test_protocol_v2.js
```

## Prueba de concurrencia

Los servidores V1 y V2 usan un `ThreadPoolExecutor`. `--workers` controla la cantidad de solicitudes que pueden procesarse concurrentemente y `--processing-delay-ms` introduce una demora exclusivamente demostrativa.

Inicie V2 directamente, sin el proxy, para aislar la concurrencia del servidor:

```bash
python server/server_v2.py --port 9001 --workers 4 --processing-delay-ms 1000
```

En otra terminal Git Bash, lance dos clientes con una sola instrucción:

```bash
node client/client_v2.js --port 9001 --sequence 10 --message "Cliente A" --timeout-ms 2000 --retries 1 & node client/client_v2.js --port 9001 --sequence 11 --message "Cliente B" --timeout-ms 2000 --retries 1 & wait
```

La salida del servidor debe mostrar dos líneas `START` asociadas a trabajadores distintos antes de la primera línea `END`. Esto demuestra solapamiento real. En uso normal, omita `--processing-delay-ms` o déjelo en cero.

## Protocolo V2 robustecido

V2 conserva UDP, pero incorpora CRC32, ACK/NACK, retransmisión Stop-and-Wait y deduplicación por secuencia. Use los mismos puertos y el mismo proxy; solo cambian los ejecutables del servidor y cliente:

```bash
# Terminal 1
python server/server_v2.py --port 9001

# Terminal 2: seleccione exactamente una falla
python adversary/drop_proxy.py --listen-port 9000 --server-port 9001 --drop-client-to-server 1

# Terminal 3
node client/client_v2.js --port 9000 --sequence 1 --message "Mensaje perdido" --timeout-ms 500 --retries 3
```

Repita por separado con `--corrupt-client-to-server 1` y `--duplicate-client-to-server 1`. Consulte [docs/protocol-v2.md](docs/protocol-v2.md) y [docs/error-matrix.md](docs/error-matrix.md).

Reinicie servidor y proxy entre escenarios. Si mantiene el servidor activo, asigne una secuencia diferente a cada mensaje; V2 rechaza reutilizar una secuencia con otro payload mediante `SEQUENCE_CONFLICT`.
