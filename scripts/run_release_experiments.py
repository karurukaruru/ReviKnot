"""Explicit, budgeted release experiments. Never print or persist credentials."""
import argparse
import json
from pathlib import Path

from patchcourt import providers
from patchcourt.budget import RequestBudget
from patchcourt.credentials import load_local_credentials
from patchcourt.evidence import now, sanitize, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("live", "evaluation", "lab", "reason"))
    parser.add_argument("--provider", choices=("deepseek", "nebius"), required=True)
    parser.add_argument("--model")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument('--model-calls',type=int,help='New-ledger limit, or require an exact existing limit; never adjusts a saved ledger')
    parser.add_argument('--searches',type=int,help='New-ledger search limit, or require the exact saved limit')
    parser.add_argument('--discovery-calls',type=int,help='New-ledger discovery limit, or require the exact saved limit')
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--knowledge-dir", type=Path)
    parser.add_argument("--trials", type=int, default=2)
    parser.add_argument("--tavily", action="store_true")
    parser.add_argument('--max-model-requests',type=int,help='live only: per-run inference dispatch ceiling (default 16)')
    parser.add_argument('--max-tool-turns',type=int,help='live only: conversation turns (default 8)')
    parser.add_argument('--max-repair-attempts',type=int,help='live only: proposal attempts (default 3)')
    parser.add_argument('--token-reservation-limit',type=int,help='live only: model payload/output reservation ceiling (default 400000)')
    parser.add_argument("--max-output-tokens", type=int,
                        help="Explicit output budget; reason/evaluation default 8192, live uses provider defaults. Not a claim of model capacity")
    args = parser.parse_args(argv)
    output_available = False
    try:
        if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
            raise ValueError("Use a new experiment output directory; prior records must be preserved")
        output_available = True
        if args.max_output_tokens is not None and args.mode=='lab':
            raise ValueError('--max-output-tokens is not configured by this lab runner')
        live_keys=('max_model_requests','max_tool_turns','max_repair_attempts','token_reservation_limit')
        if args.mode!='live' and any(getattr(args,name) is not None for name in live_keys):
            raise ValueError('Workflow step limits apply only to live mode')
        if args.mode=='live':
            from patchcourt.live_workflow import validate_workflow_limits
            validate_workflow_limits(**{name:getattr(args,name) for name in live_keys if getattr(args,name) is not None},max_output_tokens=args.max_output_tokens)
            if args.max_output_tokens is not None:
                providers.validate_output_tokens(args.provider,args.max_output_tokens)
        if args.mode in {"reason", "evaluation"}:
            providers.validate_output_tokens(args.provider, 8192 if args.max_output_tokens is None else args.max_output_tokens)
        budget = open_budget(args)
        load_local_credentials(args.env_file)
        with budget.applied():
            result = execute(args)
    except (ValueError, OSError, TypeError, KeyError, IndexError, AttributeError) as exc:
        failure = sanitize({"status": "ERROR", "kind": "experiment runner failure", "created_at": now(),
                            "mode": args.mode, "provider": args.provider,
                            "reason": type(exc).__name__ + ": " + str(exc),
                            "scope": "Runner stopped; inspect any preserved child records. No success is inferred."})
        if output_available:
            try:
                write_json(args.output / "experiment-failure.json", failure)
            except OSError:
                failure["failure_record"] = "Could not persist runner failure; prior request reservations remain in the budget ledger"
        print(json.dumps(failure))
        return 2
    counts = {kind: sum(row["kind"] == kind for row in budget.state["reservations"])
              for kind in budget.state["limits"]}
    print(json.dumps({"status": result.get("status"), "provider": args.provider,
                      "output": str(args.output.resolve()), "budget_reservations": counts,
                      "budget_limits":budget.limits,
                      "total_reported_tokens": result.get("total_reported_tokens")}))
    return 0 if result.get("status") in {"PASS", "COMPLETE"} else 2


def open_budget(args):
    """Use saved explicit limits; optional flags assert, never increase them."""
    explicit={name:getattr(args,name) for name in ('model_calls','searches','discovery_calls') if getattr(args,name) is not None}
    if args.budget.exists():
        budget=RequestBudget.from_existing(args.budget)
        if any(budget.limits[name]!=value for name,value in explicit.items()):
            raise ValueError('Saved budget limits differ; adjust explicitly with reviknot budget LEDGER --reason before running')
        return budget
    return RequestBudget(args.budget,**explicit)


def execute(args):
    if args.mode == "live":
        from patchcourt.live_workflow import run_live_workflow
        return run_live_workflow(args.output, provider=args.provider, model=args.model,
                                 use_tavily=args.tavily, knowledge_dir=args.knowledge_dir,
                                 **{name:getattr(args,name) for name in ('max_model_requests','max_tool_turns','max_repair_attempts','token_reservation_limit','max_output_tokens') if getattr(args,name) is not None})
    if args.mode == "evaluation":
        from patchcourt.release_evaluation import run_evaluation
        return run_evaluation(args.output, provider=args.provider, model=args.model, trials=args.trials, use_tavily=args.tavily,
                              max_output_tokens=8192 if args.max_output_tokens is None else args.max_output_tokens)
    if args.mode == "lab":
        if args.provider != "nebius":
            raise ValueError("Competition reliability lab requires actual Nebius access")
        from patchcourt.lab import run_lab
        return run_lab(args.output, model=args.model, trials=args.trials)
    from patchcourt.reasoning import run_reasoning
    from patchcourt.reproductions import source
    from patchcourt.counterexamples import tool_conversation
    args.output.mkdir(parents=True, exist_ok=True)
    result = run_reasoning(source("nvidia"), {"original_input": tool_conversation(),
                                             "question": "Inspect the adapter for semantic loss; propose supported controls and counterexamples."},
                           provider=args.provider, model=args.model, use_tavily=args.tavily,
                           max_output_tokens=8192 if args.max_output_tokens is None else args.max_output_tokens)
    write_json(args.output / "reasoning.json", result)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
