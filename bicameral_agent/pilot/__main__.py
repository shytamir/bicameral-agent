"""Small local owner interface. No inference occurs on import, allocation or inspection."""
import argparse
from pathlib import Path
from types import SimpleNamespace
from ..contracts.base import canonical_bytes, load_json
from ..storage import Store
from .backend import OllamaBackend
from .batch import allocate, attach, report_run, run_trajectory


def unavailable_count(text):
    raise ValueError('tokenizer required for model calls or memory edits')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    allocation = commands.add_parser('allocate', help='Allocate a recorded finite development activity')
    allocation.add_argument('package')
    allocation.add_argument('directory')
    run = commands.add_parser('run', help='Run an explicitly authorized MODEL development batch')
    run.add_argument('directory')
    run.add_argument('--tokenizer-directory', required=True)
    for name in ('status', 'pause', 'resume', 'terminate', 'inspect'):
        command = commands.add_parser(name)
        command.add_argument('store')
        if name in ('pause', 'resume', 'terminate'):
            command.add_argument('--reason', required=True)
        if name == 'inspect':
            command.add_argument('--event')
            command.add_argument('--limit', type=int, default=20)
    args = parser.parse_args(argv)
    if args.command == 'allocate':
        result = allocate(args.package, args.directory)
    elif args.command == 'run':
        directory = Path(args.directory)
        index = load_json((directory / 'batch.json').read_bytes())
        if index['version'] != '0.4' or index['status'] != 'ALLOCATED' or index['mode'] != 'MODEL':
            raise ValueError('a complete explicitly authorized MODEL allocation is required')
        result = []
        for entry in index['allocation']:
            if Path(entry['file']).name != entry['file']:
                raise ValueError('Run stores must be direct children of the batch directory')
            store = Store(directory / entry['file'], busy_timeout_ms=1000)
            try:
                run_id = store._db.execute('SELECT id FROM runs').fetchone()[0]
                config = store.configuration(run_id)
                backend = OllamaBackend(load_json(_artifact(store, run_id, 'model')),
                    load_json(_artifact(store, run_id, 'settings')), args.tokenizer_directory,
                    seconds=config.budgets.call_seconds, max_bytes=config.budgets.response_bytes * 2)
                kernel, owner = attach(store, backend)
                kernel.recover()
                report = run_trajectory(kernel, owner, backend)
                result.append(report)
                if report['state'] == 'PAUSED' or any(h.status == 'HELD' for _, _, h in kernel.controls('WELFARE_HOLD')):
                    break
            finally:
                store.close()
    else:
        if not Path(args.store).is_file():
            raise ValueError('existing Run store required')
        store = Store(args.store, busy_timeout_ms=1000)
        try:
            decisions = store.removals.all()
            if decisions:
                if args.command not in {'status', 'inspect'}:
                    raise ValueError('retention keeps execution stopped')
                result = {'execution': 'STOPPED', 'removals': decisions}
            else:
                kernel, owner = attach(store, SimpleNamespace(tokenizer=SimpleNamespace(count=unavailable_count)))
                if args.command in {'pause', 'resume', 'terminate'}:
                    owner.run_control(args.command.upper(), args.reason)
                    result = report_run(kernel)
                elif args.command == 'inspect':
                    if args.event:
                        row = store._db.execute('SELECT payload_id FROM events WHERE run_id=? AND id=?',
                            (kernel.run_id, args.event)).fetchone()
                        if row is None:
                            raise ValueError('unknown event')
                        raw = store.read_payload(kernel.run_id, row[0])
                        result = {'event': args.event, 'text': raw[:65536].decode('utf-8', errors='replace'),
                                  'truncated': len(raw) > 65536}
                    else:
                        if not 1 <= args.limit <= 100:
                            raise ValueError('inspection limit must be 1..100')
                        result = store.events(kernel.run_id)[-args.limit:]
                else:
                    result = report_run(kernel)
        finally:
            store.close()
    print(canonical_bytes(result).decode())


def _artifact(store, run_id, name):
    row = store._db.execute('SELECT payload_id FROM artifacts WHERE run_id=? AND name=?', (run_id, name)).fetchone()
    return store.read_payload(run_id, row[0])


if __name__ == '__main__':
    main()
