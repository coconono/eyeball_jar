#!/usr/bin/env python3
import subprocess
import sys
import time
import configparser
import os

def is_ollama_running():
    try:
        # Check if any process contains 'ollama' in its name
        result = subprocess.run(['pgrep', '-f', 'ollama'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking Ollama status: {e}")
        return False

def main():
    debug = False
    model = None
    args = sys.argv[1:]
    interactive = False
    web = False
    # Parse flags
    if '--debug' in args:
        debug = True
        args.remove('--debug')
    if '--verbose' in args:
        debug = True
        args.remove('--verbose')
    if '--interactive' in args:
        interactive = True
        args.remove('--interactive')
    if '--web' in args:
        web = True
        args.remove('--web')
    if '--model' in args:
        idx = args.index('--model')
        if idx + 1 < len(args):
            model = args[idx + 1]
            del args[idx:idx+2]
        else:
            print("Error: --model flag requires a value.")
            sys.exit(1)
    # Read config file if model not set
    config_path = os.path.join(os.path.dirname(__file__), 'settings.cfg')
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
        if model is None:
            model = config.get('ollama', 'model', fallback=None)
    # If model is set, update config file
    if model:
        if not config.has_section('ollama'):
            config.add_section('ollama')
        config.set('ollama', 'model', model)
        with open(config_path, 'w') as f:
            config.write(f)
    if not interactive and len(args) < 1:
        print("Usage: python3 eyeball_jar.py 'Your question here' [--debug] [--model MODEL] [--interactive] [--web]")
        sys.exit(1)
    if not interactive:
        question = args[0]
        print(f"Question: {question}")
    if web:
        # Use ddgr to search the web and summarize results with Ollama
        try:
            if debug:
                print("[DEBUG] Starting ddgr subprocess...")
            ddgr_failed = False
            try:
                ddgr_result = subprocess.run([
                    "ddgr",
                    "--noprompt",
                    "--json",
                    "-n", "5",
                    "--url-handler", "echo",
                    question
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            except FileNotFoundError:
                if debug:
                    print("[ERROR] ddgr is not installed or not found in PATH. Please install ddgr to use the --web feature.")
                ddgr_failed = True
            except subprocess.TimeoutExpired:
                if debug:
                    print("[ERROR] ddgr subprocess timed out after 10 seconds. Is ddgr waiting for input or not installed?")
                ddgr_failed = True
            if not ddgr_failed and debug:
                print(f"[DEBUG] ddgr return code: {ddgr_result.returncode}")
                print(f"[DEBUG] ddgr stdout:\n{ddgr_result.stdout}")
                print(f"[DEBUG] ddgr stderr:\n{ddgr_result.stderr}")
            if not ddgr_failed:
                if ddgr_result.returncode != 0 or 'http error' in ddgr_result.stderr.lower() or '202' in ddgr_result.stderr:
                    if debug:
                        print(f"[ERROR] Failed to get web results from ddgr. Error: {ddgr_result.stderr.strip()}")
                        print("[HINT] DuckDuckGo may be rate-limiting or blocking automated queries. Will use the search results URL instead.")
                    ddgr_failed = True
            if not ddgr_failed:
                web_results = ddgr_result.stdout.strip()
                if debug:
                    print("Top web results:\n" + web_results)
                prompt = f"Summarize the following web search results in a concise paragraph for the question: '{question}'.\n\nResults:\n{web_results} do not mention you are summarizing."
                ollama_input = prompt
            else:
                # Fallback: pass the DuckDuckGo search URL to Ollama
                search_url = f"https://duckduckgo.com/?q={question.replace(' ', '+')}"
                if debug:
                    print(f"[INFO] Passing search URL to Ollama: {search_url}")
                prompt = f"Visit the following DuckDuckGo search results page and summarize the most relevant information for the question. do not mention you are summarizing. '{question}'.\n\nURL: {search_url}"
                ollama_input = prompt
            if not ollama_input:
                print("[ERROR] Could not construct a prompt for Ollama.")
                sys.exit(1)
            if debug:
                print("[DEBUG] Checking Ollama status...")
            # Summarize with Ollama
            if not is_ollama_running():
                print("Ollama is NOT running. Attempting to start Ollama...")
                try:
                    if debug:
                        print("[DEBUG] Launching ollama serve...")
                    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    for i in range(10):
                        if debug:
                            print(f"[DEBUG] Waiting for Ollama... ({i+1}/10)")
                        time.sleep(1)
                        if is_ollama_running():
                            print("jiggling the eyeball jar")
                            break
                    else:
                        print("Failed to start Ollama.")
                        sys.exit(1)
                except Exception as e:
                    print(f"Error starting Ollama: {e}")
                    sys.exit(1)
            else:
                print("jiggling the eyeball jar")
            if not model:
                print("Error: No model specified. Use --model flag or set in settings.cfg.")
                sys.exit(1)
            if debug:
                print("[DEBUG] Calling Ollama for summary...")
            result = subprocess.run([
                "ollama", "run", model, ollama_input
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if debug:
                print(f"[DEBUG] Ollama return code: {result.returncode}")
                print(f"[DEBUG] Ollama stdout:\n{result.stdout}")
                print(f"[DEBUG] Ollama stderr:\n{result.stderr}")
            if debug:
                print("--- DEBUG: Ollama CLI stdout ---")
                print(result.stdout)
                print("--- DEBUG: Ollama CLI stderr ---")
                print(result.stderr)
                print(f"--- DEBUG: Return code: {result.returncode} ---")
            if result.returncode == 0:
                print("the eyeballs speak:")
                print(f"\033[92m{result.stdout.strip()}\033[0m")
            else:
                print(f"Failed to get summary from Ollama CLI. Error: {result.stderr.strip()}")
        except Exception as e:
            print(f"Error during web search or summarization: {e}")
        return
    # ...existing code...
    try:
        if not model:
            print("Error: No model specified. Use --model flag or set in settings.cfg.")
            sys.exit(1)
        if interactive:
            print("Entering interactive mode. Type 'exit' or 'quit' to leave.")
            while True:
                user_input = input("You: ")
                if user_input.strip().lower() in ["exit", "quit"]:
                    print("Exiting interactive mode.")
                    break
                result = subprocess.run([
                    "ollama", "run", model, user_input
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if debug:
                    print("--- DEBUG: Ollama CLI stdout ---")
                    print(result.stdout)
                    print("--- DEBUG: Ollama CLI stderr ---")
                    print(result.stderr)
                    print(f"--- DEBUG: Return code: {result.returncode} ---")
                if result.returncode == 0:
                    print("the eyeballs speak:")
                    print(f"\033[92m{result.stdout.strip()}\033[0m")
                else:
                    print(f"Failed to get response from Ollama CLI. Error: {result.stderr.strip()}")
        else:
            result = subprocess.run([
                "ollama", "run", model, question
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if debug:
                print("--- DEBUG: Ollama CLI stdout ---")
                print(result.stdout)
                print("--- DEBUG: Ollama CLI stderr ---")
                print(result.stderr)
                print(f"--- DEBUG: Return code: {result.returncode} ---")
            if result.returncode == 0:
                print("the eyeballs speak:")
                print(f"\033[92m{result.stdout.strip()}\033[0m")
            else:
                print(f"Failed to get response from Ollama CLI. Error: {result.stderr.strip()}")
    except Exception as e:
        print(f"Error communicating with Ollama CLI: {e}")

if __name__ == "__main__":
    main()
