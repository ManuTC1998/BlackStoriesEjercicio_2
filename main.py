import argparse
import os
from datetime import datetime
import textwrap
from colorama import Fore, Style, init
from dotenv import load_dotenv
import google.generativeai as genai
import ollama
import time

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

# --- Carga de Variables de Entorno ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# --- Configuración de la Carpeta de Prompts ---
PROMPTS_DIR = "prompts"
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
        juez_model = load_model(args.m1, GEMINI_API_KEY, OLLAMA_BASE_URL)
        detective_model = load_model(args.m2, GEMINI_API_KEY, OLLAMA_BASE_URL)
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
            La historia debe ser de COMPLEJIDAD MEDIA/ALTA, requiriendo 5-7 preguntas clave para deducir la solución.
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
        3.  Regla de Respuesta: Solo puedes responder ESTRICTAMENTE con una de estas tres palabras: 'Sí', 'No', o 'Irrelevante'.
        4.  No uses emojis ni texto que no sea Castellano (excepto términos técnicos).
        5.  No uses usted.
        6.  No uses español neutro o latino americano.
    """).strip()

    DETECTIVE_SYSTEM_PROMPT = textwrap.dedent("""
        Eres la IA Detective en un juego de Black Story. Tu rol es resolver un misterio formulando preguntas de Sí/No.
        Restricciones CRÍTICAS:
        1.  Idioma de Salida: SIEMPRE en Castellano.
        2.  Restricción de Conocimiento: NO conoces el misterio ni la solución.
        3.  Estrategia: Solo puedes formular preguntas de respuesta cerrada (Sí/No).
        4.  Razonamiento Interno: Antes de cada pregunta, realiza un paso de 'Razonamiento' interno. Este razonamiento NO se muestra en la terminal.
            Debe guiar la evaluación de tu hipótesis actual y la formulación de la siguiente pregunta para mejorar la calidad de tus deducciones.
            Formato de salida para la pregunta:
            ```json
            {
                "RAZONAMIENTO": "[Tu razonamiento interno aquí, NO VISIBLE EN TERMINAL]",
                "PREGUNTA": "[Tu pregunta de Sí/No aquí]"
            }
            ```
            Asegúrate de que tu respuesta contenga ÚNICAMENTE el bloque de código JSON con el formato especificado, sin texto introductorio ni de cierre.
        5.  Intento de Resolución: Cuando se te indique, intenta una solución. Este intento DEBE comenzar con la palabra clave: 'SOLUCIÓN:'.
        6.  No uses emojis ni texto que no sea Castellano (excepto términos técnicos).
        7.  No uses usted.
        8.  No uses español neutro o latino americano.
    """).strip()

    # --- Generación de la Historia por el Juez ---
    print_color("Juez, por favor, crea una Black Story.", Fore.CYAN)
    
    judge_story_prompt = JUDGE_SYSTEM_PROMPT + "\n\nCrea una nueva Black Story de complejidad media/alta."
    
    try:
        story_response = juez_model.generate(judge_story_prompt)
        
        story_short = ""
        story_long = ""
        solution = ""

        # Extraer el contenido JSON de forma más flexible
        json_start = story_response.find("{")
        json_end = story_response.rfind("}")

        if json_start != -1 and json_end != -1 and json_start < json_end:
            json_content = story_response[json_start : json_end + 1].strip()
            
            import json
            try:
                parsed_response = json.loads(json_content)
                story_short = parsed_response.get("HISTORIA_CORTA", "").strip()
                story_long = parsed_response.get("HISTORIA_LARGA", "").strip()
                solution = parsed_response.get("SOLUCION", "").strip()
            except json.JSONDecodeError:
                raise ValueError("El Juez no generó un JSON válido.")

        if not (story_short and story_long and solution):
            raise ValueError("El Juez no generó la historia o solución en el formato esperado.")

        # Guardar historia larga y solución
        timestamp = datetime.now().strftime("%d-%m-%Y %H-%M")
        filename = os.path.join(PROMPTS_DIR, f"{timestamp}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- Historia Larga ---\n{story_long}\n\n--- Solución ---\n{solution}\n")
        
        print_color(get_bubble_ascii(f"Historia y solución guardadas en {filename}", "Sistema", Fore.CYAN), Fore.CYAN)

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

            # Detective formula una pregunta
            detective_prompt = DETECTIVE_SYSTEM_PROMPT + f"\n\nHistoria: {story_short}\n"
            if conversation_history:
                detective_prompt += "Preguntas anteriores y respuestas:\n" + "\n".join(conversation_history)
            detective_prompt += "\nFormula tu siguiente pregunta de Sí/No."

            detective_response = detective_model.generate(detective_prompt)
            
            # Extraer el bloque de código JSON del Markdown
            json_block_start = detective_response.find("```json")
            json_block_end = detective_response.rfind("```")

            reasoning = ""
            question = ""

            if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
                json_content = detective_response[json_block_start + len("```json"):json_block_end].strip()
                
                import json
                try:
                    parsed_response = json.loads(json_content)
                    reasoning = parsed_response.get("RAZONAMIENTO", "").strip()
                    question = parsed_response.get("PREGUNTA", "").strip()
                except json.JSONDecodeError:
                    print_color(get_bubble_ascii("El Detective no generó un JSON válido dentro del bloque de código Markdown. Fin del juego.", "Sistema", Fore.RED), Fore.RED)
                    break
            
            if not question:
                print_color(get_bubble_ascii("El Detective no formuló una pregunta válida. Fin del juego.", "Sistema", Fore.RED), Fore.RED)
                break

            print_color(get_bubble_ascii(question, f"Detective ({detective_model.name})", Fore.RED), Fore.RED)
            input("[PULSA INTRO PARA CONTINUAR]")

            # Juez responde a la pregunta
            judge_answer_prompt = JUDGE_SYSTEM_PROMPT + f"\n\nHistoria: {story_short}\nSolución: {solution}\nPregunta del Detective: {question}\n\nResponde estrictamente con 'Sí', 'No' o 'Irrelevante'."
            judge_answer = juez_model.generate(judge_answer_prompt).strip()

            if judge_answer not in ["Sí", "No", "Irrelevante"]:
                print_color(get_bubble_ascii(f"El Juez dio una respuesta inválida: '{judge_answer}'. Fin del juego.", "Sistema", Fore.RED), Fore.RED)
                break

            print_color(get_bubble_ascii(judge_answer, f"Juez ({juez_model.name})", Fore.GREEN), Fore.GREEN)
            input("[PULSA INTRO PARA CONTINUAR]")

            # Añadir al historial de conversación
            conversation_history.append(f"Detective: {question}")
            conversation_history.append(f"Juez: {judge_answer}")

            # Intento de solución del Detective cada 7 turnos
            if turn_count % 7 == 0:
                print_color(get_bubble_ascii("Detective, es hora de intentar una solución.", "Sistema", Fore.CYAN), Fore.CYAN)
                detective_solution_prompt = DETECTIVE_SYSTEM_PROMPT + f"\n\nHistoria: {story_short}\n"
                if conversation_history:
                    detective_solution_prompt += "Preguntas y respuestas anteriores:\n" + "\n".join(conversation_history)
                detective_solution_prompt += "\nIntenta resolver el misterio. Comienza tu respuesta con 'SOLUCIÓN:'."
                
                solution_attempt = detective_model.generate(detective_solution_prompt).strip()
                
                if solution_attempt.startswith("SOLUCIÓN:"):
                    print_color(get_bubble_ascii(solution_attempt, f"Detective ({detective_model.name})", Fore.RED), Fore.RED)
                    input("[PULSA INTRO PARA CONTINUAR]")
                    
                    # Comparar solución (simplificado por ahora)
                    # Una comparación más robusta podría implicar que el Juez evalúe la solución del Detective.
                    # Por ahora, una simple comparación de texto en minúsculas.
                    if solution_attempt.replace("SOLUCIÓN:", "").strip().lower() == solution.lower():
                        print_color(get_bubble_ascii("¡El Detective ha resuelto el misterio! Fin del juego.", "Sistema", Fore.GREEN), Fore.GREEN)
                        break
                    else:
                        print_color(get_bubble_ascii("El Detective no ha acertado la solución. Continúa el juego.", "Sistema", Fore.YELLOW), Fore.YELLOW)
                        input("[PULSA INTRO PARA CONTINUAR]")
                else:
                    print_color(get_bubble_ascii("El Detective no formuló la solución correctamente. Continúa el juego.", "Sistema", Fore.YELLOW), Fore.YELLOW)
                    input("[PULSA INTRO PARA CONTINUAR]")

    except Exception as e:
        print_color(get_bubble_ascii(f"Ocurrió un error durante el juego: {e}", "Sistema", Fore.RED), Fore.RED)

if __name__ == "__main__":
    main()
