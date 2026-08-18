# Matriz de errores y soluciones

| Falla inyectada | Comportamiento observado en V1 | Mecanismo de V2 | Resultado esperado en V2 |
| --- | --- | --- | --- |
| Pérdida del primer datagrama | El cliente termina por timeout y el servidor no recibe el mensaje. | ACK, timeout y retransmisión Stop-and-Wait. | El cliente retransmite y recibe ACK; el servidor procesa una vez. |
| Corrupción de un byte | El servidor acepta el payload alterado porque la longitud sigue siendo válida. | CRC32, NACK y retransmisión. | El servidor descarta el intento corrupto, envía NACK y procesa la copia intacta. |
| Duplicación del mensaje | El servidor procesa dos veces la misma secuencia. | Caché de ACK y deduplicación por secuencia. | El servidor procesa una vez y responde al duplicado con el ACK almacenado. |
| Solicitudes simultáneas | El procesamiento secuencial puede bloquear solicitudes posteriores si una operación tarda. | Pool de trabajadores y estado compartido protegido con bloqueo. | Dos clientes se procesan de forma solapada sin corromper la caché de respuestas. |

## Método experimental

1. Mantener sin cambios el servidor, cliente y formato de V1 durante sus tres pruebas.
2. Seleccionar una sola falla por ejecución mediante el proxy.
3. Registrar consola del cliente, proxy y servidor, además de la captura Wireshark.
4. Repetir los mismos mensajes, secuencias y fallas con V2.
5. Comparar el resultado observable antes y después del robustecimiento.
