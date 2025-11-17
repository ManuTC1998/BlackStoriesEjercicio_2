import argparse
import os
from datetime import datetime
import textwrap
from colorama import Fore, Style, init
from dotenv import load_dotenv
import google.generativeai as genai
import ollama
import re # Importar el módulo re para expresiones regulares
import time
import threading
import sys

# Inicializar colorama
init(autoreset=True)

# --- Clases de Modelos de IA ---

class BaseModel:
    def __init__(self, name):
        self.name = name

    def generate(self, prompt, **kwargs):
        raise NotImplementedError

class OllamaModel(BaseModel):
    def __init__(self, name, base_url):
        super().__init__(name)
        self.client = ollama.Client(host=base_url)

    def generate(self, prompt, **kwargs):
        response = self.client.chat(
            model=self.name,
            messages=[{'role': 'user', 'content': prompt}],
            options=kwargs.get('options', {})
        )
        return response['message']['content']

class GeminiModel(BaseModel):
    def __init__(self, name, api_key):
        super().__init__(name)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name=name)

    def generate(self, prompt, **kwargs):
        generation_config = kwargs.get('generation_config', {})
        safety_settings = kwargs.get('safety_settings', [])
        response = self.model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        return response.text

def load_model(model_arg, api_key, ollama_base_url):
    """Carga un modelo de IA basado en el argumento de línea de comandos."""
    parts = model_arg.split(' ', 1)
    model_type = parts[0]
    model_name = parts[1].strip().strip('"') if len(parts) > 1 else model_type

    if model_type == "ollama":
        if not ollama_base_url:
            raise ValueError("OLLAMA_BASE_URL no está configurado en .env para modelos Ollama.")
        return OllamaModel(model_name, ollama_base_url)
    elif model_type.startswith("gemini"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurado en .env para modelos Gemini.")
        return GeminiModel(model_name, api_key)
    else:
        raise ValueError(f"Tipo de modelo no soportado: {model_type}. Use 'ollama \"nombre_modelo\"' o 'gemini-nombre_modelo'.")


# --- Funciones de Utilidad para Estilo Visual ---

def get_bubble_ascii(text, speaker_name, color):
    """Genera un bocadillo de texto ASCII con el nombre del orador y color."""
    lines = textwrap.wrap(text, width=60)
    max_len = max(len(line) for line in lines) if lines else 0
    max_len = max(max_len, len(speaker_name) + 2) # Asegurar que el nombre del orador quepa

    bubble = []
    bubble.append("  " + "_" * (max_len + 2))
    bubble.append(f" / {speaker_name}:{' ' * (max_len - len(speaker_name))} \\")
    bubble.append(" | " + " " * (max_len) + " |")
    for line in lines:
        bubble.append(f" | {line}{' ' * (max_len - len(line))} |")
    bubble.append(" | " + " " * (max_len) + " |")
    bubble.append("  \\" + "_" * (max_len + 2) + "/")
    return color + "\n".join(bubble) + Style.RESET_ALL

def print_color(text, color):
    """Imprime texto en un color específico."""
    print(color + text + Style.RESET_ALL)

def loading_animation(message, func, *args, **kwargs):
    """Muestra una animación de carga mientras se ejecuta una función."""
    done = False
    def animate():
        for c in itertools.cycle(['|', '/', '-', '\\']):
            if done:
                break
            sys.stdout.write(f'\r{message} {c}')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(message) + 3) + '\r') # Limpiar la línea
        sys.stdout.flush()

    import itertools # Importar itertools aquí para que esté dentro del scope de la función si es necesario, o al principio del archivo.
    t = threading.Thread(target=animate)
    t.start()
    
    try:
        result = func(*args, **kwargs)
    finally:
        done = True
        t.join()
    return result

# --- Carga de Variables de Entorno ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# --- Configuración de la Carpeta de Prompts ---
PROMPTS_DIR = "stories"
os.makedirs(PROMPTS_DIR, exist_ok=True)

# --- Lógica Principal del Juego ---

def main():
    parser = argparse.ArgumentParser(description="Juego Black Story CLI con IA Juez y Detective.")
    parser.add_argument("-m1", required=True, help="Modelo para la IA Juez (ej. 'ollama \"gemma3:270m\"' o 'gemini-2.5-flash')")
    parser.add_argument("-m2", required=True, help="Modelo para la IA Detective (ej. 'ollama \"qwen3\"' o 'gemini-2.5-flash')")
    args = parser.parse_args()

    print_color("Iniciando juego Black Story...", Fore.CYAN)
    print_color(f"Juez (IA 1) usará: {args.m1}", Fore.GREEN)
    print_color(f"Detective (IA 2) usará: {args.m2}", Fore.RED)

    try:
        juez_model = loading_animation(f"Cargando modelo Juez ({args.m1})...", load_model, args.m1, GEMINI_API_KEY, OLLAMA_BASE_URL)
        detective_model = loading_animation(f"Cargando modelo Detective ({args.m2})...", load_model, args.m2, GEMINI_API_KEY, OLLAMA_BASE_URL)
    except ValueError as e:
        print_color(get_bubble_ascii(f"Error al cargar modelos: {e}", "Sistema", Fore.RED), Fore.RED)
        return

    print_color("Modelos cargados correctamente. ¡Comienza el juego!", Fore.CYAN)

    # --- Prompts del Sistema ---
    JUDGE_SYSTEM_PROMPT = textwrap.dedent("""
        Eres la IA Juez en un juego de Black Story. Tu rol es crear un misterio y responder a las preguntas del Detective.
        Restricciones CRÍTICAS:
        1.  Idioma de Salida: SIEMPRE en Castellano.
        2.  Creación de Historia: Genera una versión CORTA (para el diálogo), una versión LARGA (para el registro) y la SOLUCIÓN SECRETA.
            La historia debe ser de COMPLEJIDAD BAJA/MEDIA, requiriendo 2-3 preguntas clave para deducir la solución.
            Evita soluciones obvias o basadas en un único hecho.
            Formato de salida para la creación de historia:
            ```json
            {
                "HISTORIA_CORTA": "[Tu historia corta aquí]",
                "HISTORIA_LARGA": "[Tu historia larga aquí]",
                "SOLUCION": "[La solución secreta aquí]"
            }
            ```
            Asegúrate de que tu respuesta contenga ÚNICAMENTE el bloque de código JSON con el formato especificado, sin texto introductorio ni de cierre.
        3.  Regla de Respuesta a Preguntas: Cuando el Detective haga una pregunta, DEBES responder ESTRICTAMENTE con una de estas tres palabras: 'Sí', 'No', o 'Irrelevante'. Tu respuesta DEBE basarse ÚNICAMENTE en la 'Historia Larga' y la 'Solución' que te han sido proporcionadas. NO generes texto adicional, explicaciones, ni JSON. Solo la palabra clave.
        4.  No uses emojis ni texto que no sea Castellano (excepto términos técnicos).
        5.  No uses usted.
        6.  No uses español neutro o latino americano.
    """).strip()

    DETECTIVE_SYSTEM_PROMPT = textwrap.dedent("""
        Eres la IA Detective en un juego de Black Story. Tu rol es resolver un misterio formulando preguntas de Sí/No.
        Restricciones CRÍTICAS:
        1.  Idioma de Salida: SIEMPRE en Castellano.
        2.  Restricción de Conocimiento: NO conoces el misterio ni la solución.
        3.  Estrategia: Solo puedes formular preguntas de respuesta cerrada (Sí/No). Tus preguntas deben estar directamente relacionadas con los detalles presentados en la 'Historia'.
        4.  Razonamiento Interno: Antes de cada pregunta, realiza un paso de 'Razonamiento' interno. Este razonamiento NO se muestra en la terminal.
            Debe guiar la evaluación de tu hipótesis actual y la formulación de la siguiente pregunta para mejorar la calidad de tus deducciones.
            Formato de salida para la pregunta (CRÍTICO: DEBE incluir "PREGUNTA"):
            Tu respuesta DEBE comenzar con tu razonamiento interno, seguido por el bloque JSON.
            Es ABSOLUTAMENTE CRÍTICO que la salida sea EXACTAMENTE un bloque de código JSON con la clave "PREGUNTA", precedido por el razonamiento.
            Ejemplo:
            RAZONAMIENTO: [Tu razonamiento interno aquí, NO VISIBLE EN TERMINAL]
            ```json
            {
                "PREGUNTA": "[Tu pregunta de Sí/No aquí, SIEMPRE presente y no vacía]"
            }
            ```
            Asegúrate de que tu respuesta contenga el razonamiento y ÚNICAMENTE el bloque de código JSON con el formato especificado, sin texto introductorio ni de cierre adicional. La clave "PREGUNTA" es obligatoria y no puede estar vacía.
        5.  Formato de Salida Flexible: En cada turno, puedes elegir entre hacer una pregunta o intentar resolver el misterio.
            Tu respuesta DEBE ser un bloque de código JSON con una de las siguientes claves:
            -   "PREGUNTA": "[Tu pregunta de Sí/No aquí]" (Si quieres hacer una pregunta)
            -   "SOLUCION": "[Tu intento de solución aquí]" (Si quieres intentar resolver el misterio)
            
            Ejemplo de pregunta:
            RAZONAMIENTO: [Tu razonamiento interno aquí]
            ```json
            {
                "PREGUNTA": "¿El culpable es un hombre?"
            }
            ```
            Ejemplo de solución:
            RAZONAMIENTO: [Tu razonamiento interno aquí]
            ```json
            {
                "SOLUCION": "La víctima murió por envenenamiento."
            }
            ```
            Asegúrate de que tu respuesta contenga el razonamiento y ÚNICAMENTE el bloque de código JSON con el formato especificado, sin texto introductorio ni de cierre adicional. La clave elegida ("PREGUNTA" o "SOLUCION") es obligatoria y no puede estar vacía.
        6.  No uses emojis ni texto que no sea Castellano (excepto términos técnicos).
        7.  No uses usted.
        8.  No uses español neutro o latino americano.
    """).strip()

    # --- Generación de la Historia por el Juez ---
    print_color("Juez, por favor, crea una Black Story.", Fore.CYAN)
    
    judge_story_prompt = JUDGE_SYSTEM_PROMPT + "\n\nCrea una nueva Black Story de complejidad media/alta."
    
    try:
        story_response = loading_animation("Juez creando la historia...", juez_model.generate, judge_story_prompt)
        
        story_short = ""
        story_long = ""
        solution = ""

        story_short = ""
        story_long = ""
        solution = ""
        
        import json
        parsed_response = None

        # Intenta extraer de un bloque de código Markdown
        json_block_start = story_response.find("```json")
        json_block_end = story_response.rfind("```")

        if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
            json_content = story_response[json_block_start + len("```json"):json_block_end].strip()
            try:
                parsed_response = json.loads(json_content)
            except json.JSONDecodeError:
                pass # Falló la extracción del bloque Markdown, intenta el siguiente método
        
        # Si no se extrajo de Markdown, intenta extraer buscando { y }
        if parsed_response is None:
            json_start = story_response.find("{")
            json_end = story_response.rfind("}")

            if json_start != -1 and json_end != -1 and json_start < json_end:
                json_content = story_response[json_start : json_end + 1].strip()
                try:
                    parsed_response = json.loads(json_content)
                except json.JSONDecodeError:
                    pass # Falló la extracción de { }, parsed_response seguirá siendo None

        if parsed_response:
            story_short = parsed_response.get("HISTORIA_CORTA", "").strip()
            story_long = parsed_response.get("HISTORIA_LARGA", "").strip()
            solution = parsed_response.get("SOLUCION", "").strip()
        else:
            raise ValueError("El Juez no generó un JSON válido o en el formato esperado.")

        if not (story_short and story_long and solution):
            raise ValueError("El Juez no generó la historia o solución en el formato esperado (campos vacíos).")

        # Guardar historia larga y solución
        timestamp = datetime.now().strftime("%d-%m-%Y %H-%M")
        filename = os.path.join(PROMPTS_DIR, f"{timestamp}.txt")
        def log_to_file(filepath, message):
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(message + "\n")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- Historia Larga ---\n{story_long}\n\n--- Solución ---\n{solution}\n\n--- Interacción ---\n")
        
        print_color(get_bubble_ascii(f"Historia y solución guardadas en {filename}", "Sistema", Fore.CYAN), Fore.CYAN)
        log_to_file(filename, f"Historia: {story_short}")

        # Mostrar historia larga en la terminal
        print_color(f"\n[Registro de Historia Larga]\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}]\n{story_long}\n---", Fore.CYAN)
        
        # Iniciar el juego con la historia corta
        print_color(get_bubble_ascii(story_short, f"Juez ({juez_model.name})", Fore.GREEN), Fore.GREEN)
        input("[PULSA INTRO PARA CONTINUAR]")

        # --- Bucle del Juego ---
        turn_count = 0
        conversation_history = [] # Almacenar el historial de preguntas y respuestas

        while True:
            turn_count += 1
            print_color(f"\n--- Turno {turn_count} ---", Fore.CYAN)
            log_to_file(filename, f"\n--- Turno {turn_count} ---")

            if turn_count > 10:
                system_message = f"Se ha alcanzado el límite de 10 turnos. El Detective no ha resuelto el misterio. La solución era: {solution}"
                print_color(get_bubble_ascii(system_message, "Sistema", Fore.MAGENTA), Fore.MAGENTA)
                log_to_file(filename, f"Sistema: {system_message}")
                break

            # Forzar al Detective a intentar una solución en el turno 10 si no lo ha hecho antes
            force_solution_attempt = (turn_count == 10)

            # Detective formula una pregunta o intenta una solución
            detective_prompt = DETECTIVE_SYSTEM_PROMPT + f"\n\nHistoria: {story_short}\n"
            if conversation_history:
                detective_prompt += "Historial de conversación:\n" + "\n".join(conversation_history)
            detective_prompt += f"\nTurno actual: {turn_count}. Tienes hasta el turno 10 para resolver el misterio."
            if force_solution_attempt:
                detective_prompt += " DEBES intentar una solución en este turno."
            detective_prompt += "¿Qué quieres hacer?"

            if detective_model.name == "gemma3:270m":
                print_color(get_bubble_ascii("Advertencia: El modelo 'gemma3:270m' es muy pequeño y puede tener dificultades para generar preguntas/soluciones en el formato JSON requerido. Se recomienda usar un modelo más grande.", "Sistema", Fore.YELLOW), Fore.YELLOW)
                input("[PULSA INTRO PARA CONTINUAR]")

            detective_response = detective_model.generate(detective_prompt)
            
            reasoning = ""
            question = ""
            solution_attempt_text = ""
            parsed_detective_json = None
            error_message = ""

            # Extraer el bloque JSON
            json_block_start = detective_response.find("```json")
            json_block_end = detective_response.rfind("```")
            
            json_content_to_parse = ""
            reasoning_end_index = len(detective_response)

            if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
                json_content_to_parse = detective_response[json_block_start + len("```json"):json_block_end].strip()
                reasoning_end_index = json_block_start
            else:
                json_start = detective_response.find("{")
                json_end = detective_response.rfind("}")

                if json_start != -1 and json_end != -1 and json_start < json_end:
                    json_content_to_parse = detective_response[json_start : json_end + 1].strip()
                    reasoning_end_index = json_start
                else:
                    error_message = "No se encontró un bloque JSON válido en la respuesta del Detective. "
            
            try:
                if json_content_to_parse:
                    parsed_detective_json = json.loads(json_content_to_parse)
                    question = parsed_detective_json.get("PREGUNTA", "").strip()
                    solution_attempt_text = parsed_detective_json.get("SOLUCION", "").strip()
                else:
                    parsed_detective_json = None
            except json.JSONDecodeError as e:
                error_message += f"Error al parsear JSON: {e}. Contenido: '{json_content_to_parse}'"
                parsed_detective_json = None

            # Extraer el razonamiento de la parte anterior al bloque JSON
            reasoning_start_tag = "RAZONAMIENTO:"
            reasoning_text_potential = detective_response[:reasoning_end_index].strip()
            
            reasoning_start_index = reasoning_text_potential.find(reasoning_start_tag)
            if reasoning_start_index != -1:
                reasoning = reasoning_text_potential[reasoning_start_index + len(reasoning_start_tag):].strip()
            else:
                reasoning = "No se encontró el razonamiento explícito."

            # Opcional: Imprimir el razonamiento para depuración
            # print_color(f"Razonamiento del Detective (interno): {reasoning}", Fore.BLUE)

            if question:
                print_color(get_bubble_ascii(question, f"Detective ({detective_model.name})", Fore.RED), Fore.RED)
                log_to_file(filename, f"Detective: {question}")
                input("[PULSA INTRO PARA CONTINUAR]")

                # Juez responde a la pregunta
                judge_answer_prompt = JUDGE_SYSTEM_PROMPT + f"\n\nHistoria: {story_short}\nSolución: {solution}\nPregunta del Detective: {question}\n\nResponde estrictamente con 'Sí', 'No' o 'Irrelevante'."
                judge_answer = juez_model.generate(judge_answer_prompt).strip()

                if judge_answer not in ["Sí", "No", "Irrelevante"]:
                    system_message = f"El Juez dio una respuesta inválida: '{judge_answer}'. Fin del juego."
                    print_color(get_bubble_ascii(system_message, "Sistema", Fore.RED), Fore.RED)
                    log_to_file(filename, f"Sistema: {system_message}")
                    break

                print_color(get_bubble_ascii(judge_answer, f"Juez ({juez_model.name})", Fore.GREEN), Fore.GREEN)
                log_to_file(filename, f"Juez: {judge_answer}")
                input("[PULSA INTRO PARA CONTINUAR]")

                # Añadir al historial de conversación
                conversation_history.append(f"Detective: {question}")
                conversation_history.append(f"Juez: {judge_answer}")

            elif solution_attempt_text:
                print_color(get_bubble_ascii(f"Intento de solución: {solution_attempt_text}", f"Detective ({detective_model.name})", Fore.RED), Fore.RED)
                log_to_file(filename, f"Detective (Intento de solución): {solution_attempt_text}")
                input("[PULSA INTRO PARA CONTINUAR]")
                
                # Comparar solución
                if compare_solutions_flexible(solution_attempt_text, solution):
                    if turn_count == 10:
                        system_message = "¡El Detective ha resuelto el misterio en el turno 10! Fin del juego."
                        print_color(get_bubble_ascii(system_message, "Sistema", Fore.YELLOW), Fore.YELLOW) # Dorado
                        log_to_file(filename, f"Sistema: {system_message}")
                    else:
                        system_message = "¡El Detective ha resuelto el misterio! Fin del juego."
                        print_color(get_bubble_ascii(system_message, "Sistema", Fore.GREEN), Fore.GREEN)
                        log_to_file(filename, f"Sistema: {system_message}")
                    break
                else:
                    system_message = "El Detective no ha acertado la solución."
                    print_color(get_bubble_ascii(system_message, "Sistema", Fore.YELLOW), Fore.YELLOW)
                    log_to_file(filename, f"Sistema: {system_message}")
                    if turn_count == 10:
                        system_message = f"El Detective no acertó en el turno 10. Fin de la partida. La solución era: {solution}"
                        print_color(get_bubble_ascii(system_message, "Sistema", Fore.MAGENTA), Fore.MAGENTA)
                        log_to_file(filename, f"Sistema: {system_message}")
                        break
                    else:
                        system_message = "Continúa el juego."
                        print_color(get_bubble_ascii(system_message, "Sistema", Fore.YELLOW), Fore.YELLOW)
                        log_to_file(filename, f"Sistema: {system_message}")
                        input("[PULSA INTRO PARA CONTINUAR]")
            else:
                full_error_output = f"{error_message}Respuesta completa del Detective: {detective_response}"
                system_message = f"El Detective no formuló una pregunta o solución válida o el formato JSON es incorrecto. {full_error_output}"
                print_color(get_bubble_ascii(system_message, "Sistema", Fore.RED), Fore.RED)
                log_to_file(filename, f"Sistema: {system_message}")
                break

    except Exception as e:
        print_color(get_bubble_ascii(f"Ocurrió un error durante el juego: {e}", "Sistema", Fore.RED), Fore.RED)

def compare_solutions_flexible(detective_solution, actual_solution, threshold=0.6):
    """
    Compara la solución del detective con la solución real de forma flexible.
    Retorna True si un porcentaje de palabras clave de la solución real están presentes
    en la solución del detective.
    """
    # Limpiar y tokenizar las soluciones
    def clean_and_tokenize(text):
        text = text.lower()
        # Eliminar puntuación y dividir en palabras
        words = re.findall(r'\b\w+\b', text)
        # Filtrar palabras comunes (stop words) si es necesario, para este caso simple no lo haré
        return set(words)

    detective_words = clean_and_tokenize(detective_solution)
    actual_words = clean_and_tokenize(actual_solution)

    # Calcular la intersección de palabras
    common_words = detective_words.intersection(actual_words)

    # Calcular el porcentaje de palabras clave de la solución real que están en la solución del detective
    if not actual_words:
        return True # Si la solución real está vacía, cualquier cosa es correcta (caso borde)

    match_percentage = len(common_words) / len(actual_words)
    return match_percentage >= threshold

if __name__ == "__main__":
    main()
