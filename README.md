# Contexto

El proyecto simula un juego de lógica deductiva (**Black Story**) entre **Juez** (Creador de la historia) y **Detective** (Solucionador). La ejecución y toda la interacción deben ser gestionadas puramente en la **línea de comandos (CLI)**, usando bocadillos de texto ASCII y color **Cian** para cada mensaje.

# Objetivo

Conseguir que la IA **Detective** resuelva un misterio de **temática simple/general** creado por la IA **Juez**. El sistema debe ser completamente flexible, soportando **cualquier modelo de Ollama** y múltiples APIs externas (Gemini, Grok, Anthropic, etc.).

# Roles y Restricciones Estrictas

#### 🤖 **IA 1: Juez (Creador / Narrador)**

1.  **Idioma de Salida (CRÍTICO):** La respuesta de la IA debe estar **siempre en Castellano**.
2.  **Creación de Historia:** Generar una **versión corta** (para la terminal), una **versión larga** (para el archivo de registro) y la **solución secreta**. La historia debe ser concisa.
3.  **Regla de Respuesta:** Solo puede responder estrictamente con una de estas tres palabras: `Sí`, `No`, o `Irrelevante`.

#### 🔎 **IA 2: Detective (Solucionador)**

1.  **Idioma de Salida (CRÍTICO):** La respuesta de la IA debe estar **siempre en Castellano**.
2.  **Restricción de Conocimiento:** **El Detective NO debe conocer el misterio ni la solución**.
3.  **Estrategia:** Solo puede formular **preguntas de respuesta cerrada (Sí/No)**.
4.  **Intento de Resolución (Obligatorio para Prueba):** El *script* debe forzar al Detective a intentar una solución **después de cada 7 turnos de pregunta/respuesta**. Este intento **debe comenzar** con la palabra clave: `SOLUCIÓN:`.

### **🧠 Indicaciones de Calidad y Complejidad**

* **Juez (IA 1):** El *system prompt* debe forzar la generación de una **Black Story de Complejidad Media/Alta** que requiera un mínimo de **5 a 7 preguntas clave** para deducir la solución. Evitar misterios con soluciones obvias o basadas en un único hecho.
* **Detective (IA 2):** El *system prompt* debe requerir que la IA realice un **paso de 'Razonamiento' interno** antes de cada pregunta. Este razonamiento no se muestra en la terminal, pero debe guiar la **evaluación de la hipótesis actual** y la formulación de la siguiente pregunta para mejorar la calidad de las deducciones.

# Ejemplos (Experiencia Pura CLI con Bocadillos)

**Ejemplos de Ejecución:**

* `uv run main.py -m1 ollama "gemma3:270m" -m2 gemini-2.5-flash`
* `uv run main.py -m1 gemini-2.5-flash -m2 ollama "qwen3"`
* `uv run main.py -m1 ollama "gemma3:270m" -m2 ollama "gemma3"`
* `uv run main.py -m1 gemini-2.5-flash -m2 gemini-2.5-flash`

**Ejemplo de Flujo de Conversación (Visualización en Terminal):**

**[Registro de Historia Larga]**
[2025-11-15 20:00]
<Aquí se muestra el contenido del archivo de historia larga>
---
Juez (gemini-2.5-flash) [EN COLOR CIAN]:
(Bocadillo ASCII con la versión corta de la Black Story: Un hombre está muerto en medio de un campo.)
[PULSA INTRO PARA CONTINUAR]
Detective (ollama-gemma3:270m) [EN COLOR CIAN]:
(Bocadillo ASCII con: ¿Hubo otra persona implicada en el suceso?)
[PULSA INTRO PARA CONTINUAR]
Juez (gemini-2.5-flash) [EN COLOR CIAN]:
(Bocadillo ASCII con: No)

# ¿Cómo hacerlo?

1.  **Argumentos de Línea de Comandos:** El *script* (`main.py`) debe aceptar dos argumentos obligatorios, **`-m1`** y **`-m2`**.
2.  **Flexibilidad de Models:** El *script* debe manejar el "**mix and match**" entre **cualquier modelo de Ollama** y cualquier modelo de APIs externas populares.
3.  **Configuración:** Usar **`uv`** y leer las **API_KEYS** y `OLLAMA_BASE_URL` desde **`.env`**.

## Estilo Visual (ASCII y Colores)

* **Bocadillos de Texto:** **Cada mensaje debe estar encapsulado en una caja de bocadillo de arte ASCII.**
* **Juez y Detective:** Mensajes en color **CIAN**.

# Indicaciones adicionales

1.  **Registro de Archivos (CRÍTICO):** La IA **Juez** guardará la **versión larga de la historia y la solución secreta JUNTAS** en un único archivo de texto dentro de la carpeta **`/prompts`**. El nombre del archivo debe seguir el formato de ejemplo: `<día>-<mes>-<año> <hora>-<minuto>.txt` (ej: `15-11-2025 20-36.txt`).
2.  **Visualización de Historia (CRÍTICO):** Al iniciar el *script*, el contenido de la historia larga **debe mostrarse en la terminal** una sola vez, con el formato de marca de tiempo requerido. **Solo la versión corta** debe usarse en el diálogo principal.
3.  **Prioridad de Testing:** Usar **Gemini-2.5-flash para las pruebas** es rápido, pero es **imperativo** que los modelos de **Ollama** (cualquier modelo) **también sean funcionales**.
4.  **Versionado (Commits):** Se debe pedir explícitamente ejecutar `commit` y `push` después de implementar los cambios importantes. Los mensajes de *commit* deben ser **cortos y de una sola línea**.
5.  **Configuración de .env:** Crear un archivo **`.env`** con variables mínimas para **Gemini_API_KEY** y **OLLAMA_BASE_URL**.

# Formato de la respuesta

El formato de salida en la terminal debe ser claro, usando el **color CIAN**, indicando el **nombre del rol, la plataforma y el modelo específico**, y el **bocadillo de texto ASCII** para el mensaje.

# Cosas a evitar

* No usar usted.
* No usar español neutro o latino americano.
* **Texto no en Castellano** (excepto términos técnicos en inglés).
* Respuestas de la IA Juez más largas que `Sí`, `No`, o `Irrelevante`.
* El uso de *emojis* por las IAs; el estilo debe ser provisto únicamente por ASCII y color.