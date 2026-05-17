import argparse
import json
import os
import sys
import threading

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from bridge.debrief import format_debrief_display, generate_debrief
from bridge.detection import format_detection_display, process_thermal_detection
from bridge.gemma_client import call_gemma, check_gemma_health, parse_json_response
from bridge.mission_uploader import land, rtl, upload_mission
from bridge.preflight import format_preflight_display, run_preflight_check
from bridge.prompts import MISSION_COMMAND_INSTRUCTIONS, REPLAN_PROMPT, SYSTEM_PROMPT_BASE
from bridge.telemetry import connect_sitl, get_state, start_telemetry_threads

load_dotenv()

console = Console()
latest_output = {"text": "SARGuard online. Waiting for command.", "type": "idle"}


def process_mission_command(user_input: str) -> dict | None:
    state = get_state()
    system = SYSTEM_PROMPT_BASE.format(**state)
    user = MISSION_COMMAND_INSTRUCTIONS + f"\n\nMISSION COMMAND:\n{user_input}"
    raw = call_gemma(system, user)
    try:
        return parse_json_response(raw)
    except Exception as exc:
        console.print(f"[red]JSON parse error: {exc}[/red]")
        console.print(f"Raw response:\n{raw}")
        return None


def process_replan(user_input: str) -> dict | None:
    state = get_state()
    system = SYSTEM_PROMPT_BASE.format(**state)
    user = REPLAN_PROMPT + f"\n\nREPLAN INSTRUCTION:\n{user_input}"
    raw = call_gemma(system, user)
    try:
        return parse_json_response(raw)
    except Exception as exc:
        console.print(f"[red]Replan parse error: {exc}[/red]")
        console.print(f"Raw response:\n{raw}")
        return None


def update_overlay(text: str, output_type: str):
    latest_output["text"] = text
    latest_output["type"] = output_type


def start_overlay_server():
    from overlay.server import create_app

    app = create_app(lambda: latest_output, get_state)
    port = int(os.getenv("FLASK_PORT", "5000"))
    threading.Thread(
        target=lambda: app.run(port=port, debug=False, use_reloader=False),
        daemon=True,
    ).start()
    console.print(f"[green]Overlay server: http://localhost:{port}/[/green]")


def main():
    parser = argparse.ArgumentParser(description="SARGuard Bridge")
    parser.add_argument("--voice", action="store_true")
    parser.add_argument("--no-overlay", action="store_true")
    args = parser.parse_args()

    console.rule("[bold cyan]SARGuard - SAR Drone AI System[/bold cyan]")

    console.print("Checking Gemma server on Jetson...", end=" ")
    if check_gemma_health():
        console.print("[green]ONLINE[/green]")
    else:
        console.print("[red]UNREACHABLE[/red]")
        console.print(
            f"[yellow]Cannot reach Gemma at {os.getenv('JETSON_IP')}:{os.getenv('JETSON_GEMMA_PORT')}.\n"
            "Run jetson/start_gemma.sh on Jetson first.[/yellow]"
        )
        sys.exit(1)

    connect_sitl()
    start_telemetry_threads()

    if not args.no_overlay:
        start_overlay_server()

    console.print(
        Panel(
            "[bold]Commands:[/bold]\n"
            "  [cyan]preflight[/cyan]       - run pre-flight safety check\n"
            "  [cyan]detect[/cyan]          - inject thermal detection (Stage 5)\n"
            "  [cyan]debrief[/cyan]         - generate post-flight report (Stage 7)\n"
            "  [cyan]rtl[/cyan]             - Return To Launch\n"
            "  [cyan]land[/cyan]            - land immediately\n"
            "  [cyan]quit[/cyan]            - exit\n"
            "  [cyan]<anything else>[/cyan] - mission command or replan",
            title="SARGuard Bridge",
            border_style="cyan",
        )
    )

    in_mission = False
    while True:
        try:
            if args.voice:
                from bridge.voice import record_and_transcribe

                user_input = record_and_transcribe()
                if not user_input:
                    continue
            else:
                user_input = console.input("\n[bold cyan]Operator >[/bold cyan] ").strip()

            if not user_input:
                continue

            command = user_input.lower().strip()
            if command == "quit":
                console.print("[yellow]Exiting SARGuard.[/yellow]")
                break
            if command == "preflight":
                console.print("[cyan]Running pre-flight check...[/cyan]")
                data = run_preflight_check()
                display = format_preflight_display(data)
                console.print(display)
                update_overlay(display, "preflight")
            elif command == "detect":
                console.print("[cyan]Processing thermal detection...[/cyan]")
                data = process_thermal_detection()
                display = format_detection_display(data)
                console.print(display)
                update_overlay(display, "detection")
            elif command == "debrief":
                console.print("[cyan]Generating post-flight debrief...[/cyan]")
                data = generate_debrief()
                display = format_debrief_display(data)
                console.print(display)
                update_overlay(display, "debrief")
            elif command == "rtl":
                rtl()
                update_overlay("RTL commanded - drone returning home.", "system")
            elif command == "land":
                land()
                update_overlay("LAND commanded - immediate landing.", "system")
            elif in_mission:
                console.print("[cyan]Processing replan...[/cyan]")
                data = process_replan(user_input)
                if data:
                    display = json.dumps(data, indent=2)
                    console.print(display)
                    update_overlay(display, "replan")
                    if data.get("new_waypoints"):
                        upload_mission(data["new_waypoints"])
            else:
                console.print("[cyan]Parsing mission command...[/cyan]")
                data = process_mission_command(user_input)
                if data:
                    display = json.dumps(data, indent=2)
                    console.print_json(json.dumps(data))
                    update_overlay(display, "mission")
                    if data.get("decision") == "go" and data.get("waypoints"):
                        upload_mission(data["waypoints"])
                        in_mission = True
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
        except Exception as exc:
            console.print(f"[red]Unexpected error: {exc}[/red]")


if __name__ == "__main__":
    main()
