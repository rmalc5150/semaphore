"""Activate the disk-free capture runtime only for supervised services."""
import os
import sys
if os.environ.get('OPTIMA_S3_RUNTIME') == '1':
    try:
        import s3_runtime_fs
        s3_runtime_fs.install()
        os.environ['OPTIMA_S3_RUNTIME_ACTIVE'] = '1'
    except BaseException as exc:
        print('S3 runtime initialization failed: ' + type(exc).__name__, file=sys.stderr)
        os._exit(78)
