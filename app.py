import errno
import json
import logging
import os
import sys
from functools import wraps
from http import HTTPStatus
import locale
from shutil import copyfileobj
from time import perf_counter
from traceback import print_exception
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import psutil
from dotenv import load_dotenv
from flask import Flask, Response, request, abort
from flask_executor import Executor
from s3fs import S3FileSystem

# Auto-set locale for thousands separators in debug output
locale.setlocale(locale.LC_ALL, '')

load_dotenv()

logging.basicConfig()
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(os.environ.get('LOGLEVEL', 'INFO').upper())

shared_secret = os.environ.get('SHARED_SECRET')
if not shared_secret:
    logger.error(f'SHARED_SECRET must be set')
    sys.exit(errno.EINTR)

# Can configure one bucket as BUCKET_NAME or two buckets as INPUT_BUCKET_NAME
# and OUTPUT_BUCKET_NAME
input_bucket_name = os.environ.get('INPUT_BUCKET_NAME')
if input_bucket_name:
    output_bucket_name = os.environ.get('OUTPUT_BUCKET_NAME')
else:
    output_bucket_name = input_bucket_name = os.environ.get('BUCKET_NAME')

if not input_bucket_name:
    raise Exception("Input bucket name is not defined.")
if not output_bucket_name:
    raise Exception("Output bucket name is not defined.")

DEFAULT_COPY_BUFFER_SIZE = 1024 * 1024  # 1 MiB
copy_buffer_size = os.environ.get('COPY_BUFFER_SIZE', default=DEFAULT_COPY_BUFFER_SIZE)

b2fs = S3FileSystem(version_aware=True)

# Flask executor object
executor = None

# Check that the buckets exist in B2 before we start the app
try:
    if not b2fs.exists(f'/{input_bucket_name}'):
        logger.error(f'Cannot access bucket: {input_bucket_name}')
        sys.exit(errno.EINTR)

    elif input_bucket_name == output_bucket_name:
        logger.debug(f'Connected to B2, {input_bucket_name} exists.')
    else:
        if not b2fs.exists(f'/{output_bucket_name}'):
            logger.error(f'Cannot access bucket: {output_bucket_name}')
            sys.exit(errno.EINTR)
        logger.debug(f'Connected to B2, {input_bucket_name} and {output_bucket_name} exist.')
except Exception as e:
    logger.error(f'Cannot connect to B2: {e}')
    print_exception(e)
    sys.exit(errno.EINTR)

# Start the Flask app and Executor
app = Flask(__name__)

executor = Executor(app)


# Simple authorization via a shared secret. You could use whatever scheme you like instead.
def auth_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('authorization')
        if not auth_header or auth_header != f'Bearer {shared_secret}':
            abort(HTTPStatus.UNAUTHORIZED)
        return view_function(*args, **kwargs)
    return decorated_function


@executor.job
def make_zip_job(selected_filenames, zip_filename):
    # noinspection PyBroadException
    try:
        """
        Zip the input files from B2, writing the output file into B2
        """
        start_time = perf_counter()
        bytes_read = 0
        zip_file_path = f'{output_bucket_name}/{zip_filename}'

        logger.debug(f'Opening {zip_file_path} for writing as a ZIP')
        with b2fs.open(zip_file_path, 'wb') as f, ZipFile(f, 'w') as zipfile:
            for filename in selected_filenames:
                input_path = f'{input_bucket_name}/{filename}'
                logger.debug(f'Writing {input_path} to ZIP')

                try:
                    # Get file info, so we have a timestamp for the ZIP entry and the file size
                    # for calculating compression ratio
                    file_info = b2fs.info(input_path)
                    logger.debug(f'Input file info: {file_info}')
                    last_modified = file_info['LastModified']
                    bytes_read += file_info['size']
                    date_time = (last_modified.year, last_modified.month, last_modified.day,
                                 last_modified.hour, last_modified.minute, last_modified.second)

                    zipinfo = ZipInfo(filename=filename, date_time=date_time)
                    # You need to set the compress_type on each ZipInfo object - it is not inherited from the ZipFile!
                    zipinfo.compress_type = ZIP_DEFLATED
                    # Since we know the file size, set it so that large files work correctly
                    zipinfo.file_size = file_info['size']

                    with (b2fs.open(input_path, 'rb') as src,
                          zipfile.open(zipinfo, 'w') as dst):
                        copyfileobj(src, dst, copy_buffer_size)

                    logger.debug(f'Wrote {input_path} to ZIP')
                except FileNotFoundError:
                    logger.error(f'{input_path} not found - skipping')

        # Don't get the output file info unless we're going to log statistics!
        if logger.isEnabledFor(logging.DEBUG):
            output_file_info = b2fs.info(zip_file_path)
            bytes_written = output_file_info['size']
            compression_ratio = bytes_written / bytes_read if bytes_read != 0 else 0
            memory_usage_in_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2

            logger.debug(f'Finished writing {zip_file_path} in {perf_counter() - start_time:.3f} seconds.')
            logger.debug(f'Read {bytes_read:n} bytes, wrote {bytes_written:n} bytes, '
                         f'compression ratio was {compression_ratio * 100:.0f}%')
            logger.debug(f'Currently using {memory_usage_in_mb:.0f} MB')

    except Exception as err:
        logger.error(f'Exception zipping files', exc_info=err)


@app.post('/')
@auth_required
def make_zip_endpoint():
    """
    Endpoint accepts JSON payload of the form
    {
        "files": [
            "path/to/file1.ext",
            "path/to/file2.ext",
            ...
            "path/to/filen.ext"
        ],
        "target": "path/to/zipfile.zip"
    }
    """
    req = request.json

    logger.debug(f'Request: {json.dumps(req, indent=2)}')

    # Zip the files asynchronously, so we can return a timely response to the caller
    make_zip_job.submit(req['files'], req['target'])

    return Response(status=HTTPStatus.ACCEPTED)


if __name__ == '__main__':
    port = os.getenv('PORT', '5000')
    app.run(port=port)
