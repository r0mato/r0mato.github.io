---
layout: page
permalink: /metodologia/
title: "Metodología"
eyebrow: "Proceso"
lede: "Cómo paso de una superficie desconocida a un reporte que el equipo de seguridad puede reproducir en dos minutos."
description: "Metodología de investigación: reconocimiento pasivo, hipótesis con señal citada, control negativo obligatorio y validación ciega."
---

La mayor parte del coste de un programa de bug bounty no está en los fallos reales: está en
triar ruido. Mi proceso está construido alrededor de una idea sencilla —
**una señal no es un hallazgo hasta que sobrevive al intento de matarla**.

## 1 · Reconocimiento pasivo

Antes de enviar una sola petición de prueba, mapeo la superficie:

- Subdominios por fuentes pasivas, registros de transparencia de certificados y DNS.
- Bundles JavaScript y *source maps*: de ahí salen endpoints no documentados, nombres de
  parámetros, roles, *feature flags* y expresiones de validación del lado cliente.
- Versiones de framework y componentes de terceros, para cruzarlas con vulnerabilidades
  conocidas y con parches publicados.
- Puertas secundarias: paneles huérfanos, entornos de *staging* accesibles, APIs antiguas
  que siguen respondiendo.

El resultado es un inventario, no una lista de ataques. Esta fase no genera tráfico anómalo.

## 2 · Modelado de suposiciones

Para cada flujo escribo tres cosas por separado:

| Capa | Pregunta |
|---|---|
| Negocio | ¿Qué cree la empresa que hace este flujo? |
| Desarrollo | ¿Qué asumió quien lo implementó? |
| Código | ¿Qué hace realmente la petición? |

Donde las tres no coinciden hay un hueco. Ese hueco es el candidato a vulnerabilidad, y
genera una hipótesis concreta en lugar de un `payload` genérico lanzado a ciegas.

## 3 · Una variable por disparo

Cada prueba cambia **un solo elemento** respecto a una línea base conocida. Si cambio el
identificador, la cabecera y el método a la vez y la respuesta varía, no sé por qué varía —
y un reporte que no sabe por qué funciona no es reproducible.

## 4 · Control negativo obligatorio

Esta es la regla que más hallazgos me ha matado, y por eso es la más valiosa.

> Toda señal se repite con la misma petición **sin** la condición de ataque.
> Si el comportamiento es idéntico, no había vulnerabilidad: había una coincidencia.

Ejemplos de lo que descarta:

- Un `200 OK` que parecía acceso no autorizado, pero que el endpoint devuelve también sin
  sesión porque el recurso es público por diseño.
- Una diferencia de tiempos que resultó ser latencia de red, no una inyección ciega.
- Un identificador ajeno «accesible» que en realidad era un objeto propio con otro alias.

Sin control negativo, no escribo el reporte.

## 5 · Validación ciega

Antes de redactar, un segundo pase reproduce los pasos **sin conocer la hipótesis ni la
clase de vulnerabilidad**: solo recibe el procedimiento A, el procedimiento B y el control.
Si quien valida a ciegas no observa la diferencia, el candidato se archiva. Esto elimina el
sesgo de confirmación, que es la causa raíz de la mayoría de los reportes inválidos.

## 6 · Umbral de impacto

Un hallazgo solo se reporta si puedo responder a las cinco preguntas con un sí:

1. ¿Toca datos sensibles, dinero o integridad del sistema?
2. ¿Es pivotable hacia algo mayor?
3. ¿Está dentro del alcance autorizado?
4. ¿Afecta a confidencialidad, integridad o disponibilidad de forma concreta?
5. ¿Puedo **demostrar** el impacto, no solo describirlo?

La quinta es una puerta dura. «Teóricamente un atacante podría» no es un reporte.

## 7 · El reporte

Lo que recibe el equipo de seguridad:

- Resumen en una frase y severidad con vector CVSS justificado.
- Petición y respuesta crudas, reproducibles, con el control negativo incluido.
- Impacto expresado en términos de negocio, no de laboratorio.
- Remediación concreta a nivel de código o configuración.
- Datos de prueba propios: nunca información de usuarios reales.

## Reglas que no negocio

- No salgo del alcance publicado, ni «solo para comprobar».
- No destruyo ni modifico datos del objetivo.
- No dejo persistencia de ningún tipo.
- No uso datos de clientes reales como prueba: siempre cuentas canario mías.
- No publico nada antes de la corrección ni sin permiso del programa.
