import errno
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None


logger = logging.getLogger(os.path.basename(__file__))

# A Backblaze B2 region is inserted as a single DNS label in
# https://s3.<region>.backblazeb2.com, for example us-west-004. Keep this
# permissive so future valid region naming shapes do not block startup.
B2_REGION_PATTERN = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')
B2_CONNECT_TIMEOUT_SECONDS = 10
B2_READ_TIMEOUT_SECONDS = 60
B2_MAX_RETRY_ATTEMPTS = 5


@dataclass(frozen=True)
class B2Settings:
    application_key_id: str
    application_key: str
    endpoint_url: str
    region_name: str | None
    input_bucket_name: str
    output_bucket_name: str


def get_project_version():
    pyproject_path = Path(__file__).with_name('pyproject.toml')
    pyproject_text = pyproject_path.read_text()

    if tomllib is not None:
        return tomllib.loads(pyproject_text)['project']['version']

    version_match = re.search(r'^version\s*=\s*[\'"]([^\'"]+)[\'"]', pyproject_text, re.MULTILINE)
    if not version_match:
        logger.warning('Could not read project version from pyproject.toml')
        return '0.0.0'
    return version_match.group(1)


B2_USER_AGENT_EXTRA = f'b2-zip-files/{get_project_version()} (backblaze-b2-samples)'


def get_env_value(name, legacy_names=(), required=True, env=os.environ):
    value = env.get(name)
    if value:
        return value

    for legacy_name in legacy_names:
        value = env.get(legacy_name)
        if value:
            logger.warning('%s is deprecated; use %s instead', legacy_name, name)
            return value

    if required:
        expected_names = ' or '.join([name, *legacy_names])
        logger.error(f'{expected_names} must be set')
        sys.exit(errno.EINTR)
    return None


def get_required_env(name, legacy_names=(), env=os.environ):
    return get_env_value(name, legacy_names=legacy_names, required=True, env=env)


def get_b2_endpoint_url(region):
    if not region or not B2_REGION_PATTERN.fullmatch(region):
        logger.error(f'B2_REGION "{region}" is not safe to use in a Backblaze B2 S3 endpoint')
        sys.exit(errno.EINTR)
    return f'https://s3.{region}.backblazeb2.com'


def infer_region_from_endpoint(endpoint_url):
    parsed_endpoint = urlparse(endpoint_url)
    host = parsed_endpoint.netloc or parsed_endpoint.path
    prefix = 's3.'
    suffix = '.backblazeb2.com'
    if host.startswith(prefix) and host.endswith(suffix):
        return host[len(prefix):-len(suffix)]
    return None


def get_endpoint_config(env=os.environ):
    region = env.get('B2_REGION')
    if region:
        return get_b2_endpoint_url(region), region

    endpoint_url = get_env_value('B2_REGION', legacy_names=('AWS_ENDPOINT_URL',), env=env)
    endpoint_url = endpoint_url.rstrip('/')
    return endpoint_url, infer_region_from_endpoint(endpoint_url)


def get_bucket_config(default_bucket_name, env=os.environ):
    input_bucket_name = get_env_value(
        'B2_INPUT_BUCKET_NAME',
        legacy_names=('INPUT_BUCKET_NAME',),
        required=False,
        env=env,
    )
    output_bucket_name = get_env_value(
        'B2_OUTPUT_BUCKET_NAME',
        legacy_names=('OUTPUT_BUCKET_NAME',),
        required=False,
        env=env,
    )

    if input_bucket_name or output_bucket_name:
        if not input_bucket_name:
            logger.error('B2_INPUT_BUCKET_NAME must be set when B2_OUTPUT_BUCKET_NAME is set')
            sys.exit(errno.EINTR)
        if not output_bucket_name:
            logger.error('B2_OUTPUT_BUCKET_NAME must be set when B2_INPUT_BUCKET_NAME is set')
            sys.exit(errno.EINTR)
        return input_bucket_name, output_bucket_name

    return default_bucket_name, default_bucket_name


def load_b2_settings(env=os.environ):
    application_key_id = get_required_env(
        'B2_APPLICATION_KEY_ID',
        legacy_names=('AWS_ACCESS_KEY_ID',),
        env=env,
    )
    application_key = get_required_env(
        'B2_APPLICATION_KEY',
        legacy_names=('AWS_SECRET_ACCESS_KEY',),
        env=env,
    )
    default_bucket_name = get_required_env(
        'B2_BUCKET_NAME',
        legacy_names=('BUCKET_NAME',),
        env=env,
    )
    endpoint_url, region_name = get_endpoint_config(env=env)
    input_bucket_name, output_bucket_name = get_bucket_config(default_bucket_name, env=env)

    return B2Settings(
        application_key_id=application_key_id,
        application_key=application_key,
        endpoint_url=endpoint_url,
        region_name=region_name,
        input_bucket_name=input_bucket_name,
        output_bucket_name=output_bucket_name,
    )
