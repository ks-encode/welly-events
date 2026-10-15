"""Fetch the currently readable public events; keep prior cache on source failure.

For use by GitHub Actions. Does NOT start a localhost server.
"""
import server

if __name__ == '__main__':
    server.run_refresh([src['id'] for src in server.SOURCES])
    results = server.STATUS['results']
    good = sum(x['state'] == 'indexed' for x in results.values())
    failed = sum(x['state'] == 'failed' for x in results.values())
    print(f'Refresh attempted {len(results)} sites; indexed {good}; failed {failed}; stored {len(server.DATA["events"])} records.')
