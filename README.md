# Backblaze B2 Zip Files Example

This web app accepts a list of files to be compressed and the name of a ZIP file to be created. Since reading data from cloud object storage, compressing it, and then writing the compressed data back can take some time, the app responds with HTTP status `202 ACCEPTED` immediately it receives and parses a request, then launches a background job to perform the work.

The app is implemented in Python using the [Flask](https://flask.palletsprojects.com/) web application framework and the [flask-executor](https://github.com/dchevell/flask-executor) task queue. You can run the app in a [Docker](https://www.docker.com/) container, the [Flask development server](https://flask.palletsprojects.com/en/2.3.x/server/), or in the [Gunicorn](https://gunicorn.org/) WSGI HTTP Server.

## Create a Backblaze B2 Account, Bucket and Application Key

Follow these instructions, as necessary:

* [Create a Backblaze B2 Account](https://www.backblaze.com/sign-up/cloud-storage).
* [Create a Backblaze B2 Bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets).
* [Create an Application Key](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys#create-an-app-key) with access to the bucket you wish to use.

Be sure to copy the application key as soon as you create it, as you will not be able to retrieve it later!

## Configuration

The app reads its configuration from a set of environment variables. The easiest way to manage these in many circumstances is via a `.env` file. Copy the included `.env.template` to `.env`, or create a new `.env` file:

```console
% cp .env.template .env
```

Now edit `.env`, pasting in your application key, its ID, bucket name, and endpoint:

```dotenv
LOGLEVEL=DEBUG
AWS_ACCESS_KEY_ID='<Your Backblaze B2 Application Key ID>'
AWS_SECRET_ACCESS_KEY='<Your Backblaze B2 Application Key>'
AWS_ENDPOINT_URL='<Your bucket endpoint, prefixed with https://, for example, https://s3.us-west-004.backblazeb2.com>'
BUCKET_NAME='<Your Backblaze B2 bucket name>'
SHARED_SECRET='<A long random string known only to the app and its authorized clients>'
PORT=8000
```

You can configure different buckets for input and output files if you wish by replacing the `BUCKET_NAME` line with the following:

```dotenv
INPUT_BUCKET_NAME='<Bucket with files to be zipped>'
OUTPUT_BUCKET_NAME='<Bucket for zip files>'
```

Note that, if you do use two buckets, your application key needs to have permissions to access both.

## Running the App in Docker

The easiest way to run the app is via Docker, since it is the only prerequisite, reading the environment variables from `.env`. Gunicorn is installed in the Docker container and is configured to listen on port 8000, so you will need to use Docker's `-p` option to bind port 8000 to an available port on your machine. For example, if you wanted the Docker container to listen on port 80, you would run:

```console
% docker run -p 80:8000 --env-file .env ghcr.io/backblaze-b2-samples/b2-zip-files:latest
[2024-06-28 23:04:47 +0000] [1] [DEBUG] Current configuration:
  config: python:config.gunicorn
  wsgi_app: None
...
DEBUG:app.py:Connected to B2, my-bucket exists.
```

Once the app is running, you can [send it a request](#sending-requests-to-the-app).

You can publish the image to a repository and run it in a container on any cloud provider that supports Docker. For example, to deploy the app to AWS Fargate for Amazon ECS, you would [push your image to Amazon Elastic Container Registry](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-container-image.html#create-container-image-push-ecr), then [create an Amazon ECS Linux task for the Fargate launch type](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started-fargate.html).

## Download the Source Code

```console
% git clone git@github.com:backblaze-b2-samples/b2-zip-files.git
Cloning into 'b2-zip-files'...
remote: Enumerating objects: 60, done.
remote: Counting objects: 100% (60/60), done.
...
% cd b2-zip-files
```

## Running the App on the Local Machine

### Create a Python Virtual Environment

Virtual environments allow you to encapsulate a project's dependencies; we recommend that you create a virtual environment thus:

```console
% python3 -m venv .venv
```

You must then activate the virtual environment before installing dependencies:

```console
% source .venv/bin/activate
```

You will need to reactivate the virtual environment, with the same command, if you close your Terminal window and return to the app later.

### Install Python Dependencies

```console
% pip install -r requirements.txt

```

### Running the App in the Flask development server 

Once you have configured the app, created a virtual environment and installed the dependencies, the simplest way to run the app is in the Flask development server. By default, the app will listen on `http://127.0.0.1:5000`:

```console
% flask run
DEBUG:app.py:Connected to B2, my-bucket exists.
 * Debug mode: off
INFO:werkzeug:WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
INFO:werkzeug:Press CTRL+C to quit
```

You can use the `--host` and `--port` to configure a different interface and/or port:

```console
% flask run --host=0.0.0.0 --port=8000 
DEBUG:app.py:Connected to B2, my-bucket exists.
 * Debug mode: off
INFO:werkzeug:WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8000
 * Running on http://192.168.69.12:8000
INFO:werkzeug:Press CTRL+C to quit
...
```

Once the app is running, you can [send it a request](#sending-requests-to-the-app).

### Running the App in Gunicorn

Gunicorn does not read environment variables from a `.env` file, but you can use the shell to work around that if you are running Gunicorn from the command line:

```console
% (export $(cat .env | xargs) && gunicorn --config python:config.gunicorn app:app)
[2024-06-28 14:21:43 -0700] [56698] [INFO] Starting gunicorn 22.0.0
[2024-06-28 14:21:43 -0700] [56698] [INFO] Listening at: http://0.0.0.0:8000 (56698)
[2024-06-28 14:21:43 -0700] [56698] [INFO] Using worker: sync
[2024-06-28 14:21:43 -0700] [56711] [INFO] Booting worker with pid: 56711
[2024-06-28 14:21:43 -0700] [56712] [INFO] Booting worker with pid: 56712
[2024-06-28 14:21:43 -0700] [56713] [INFO] Booting worker with pid: 56713
DEBUG:app.py:Connected to B2, my-bucket exists.
...
```

Once the app is running, you can [send it a request](#sending-requests-to-the-app).

If you are [running Gunicorn as a service](https://docs.gunicorn.org/en/latest/deploy.html), you must ensure that you set the above variables in its environment.

## Sending Requests to the App

However you run the app, clients send requests in the same way, setting the `Authorization` and `Content-Type` HTTP headers and sending a JSON payload.

* The `Authorization` header must be of the form `Authorization: Bearer <your shared secret>`
* The `Content-Type` header must specify JSON content: `Content-Type: application/json`
* The payload must be JSON, of the form:
  ```json
  {
    "files": [
      "path/to/first/file.pdf",
      "path/to/second/file.txt",
      "path/to/third/file.csv"
    ],
    "target": "path/to/output/file.zip"
  }
  ```

For example, using `curl` with the `-i` option to send a request from the Mac/Linux command line:

```console
% curl -i -d '
{
  "files": [
    "path/to/first/file.pdf",
    "path/to/second/file.txt",
    "path/to/third/file.csv"
  ],
  "target":"path/to/output/file.zip"
}
' http://127.0.0.1:8080 -H 'Content-Type: application/json' -H 'Authorization: Bearer my-long-random-string-of-characters'
HTTP/1.1 202 ACCEPTED
Server: gunicorn
Date: Fri, 28 Jun 2024 23:17:24 GMT
Connection: close
Content-Type: text/html; charset=utf-8
Content-Length: 0
```

Note that, as mentioned above, the app responds to the request immediately with 202 `ACCEPTED`. You should be able to see the app's progress in the Flask/Gunicorn/Docker log output. For example:

```text
[2024-06-28 23:17:24 +0000] [27] [DEBUG] POST /
DEBUG:app.py:Request: {
  "files": [
    "path/to/first/file.pdf",
    "path/to/second/file.txt",
    "path/to/third/file.csv"
  ],
  "target":"path/to/output/file.zip"
}
DEBUG:app.py:Opening my-bucket/path/to/output/file.zip for writing as a ZIP
DEBUG:app.py:Writing my-bucket/path/to/first/file.pdf to ZIP
DEBUG:app.py:Wrote my-bucket/path/to/first/file.pdf to ZIP
...
DEBUG:app.py:Finished writing my-bucket/path/to/output/file.zip in 11.175 seconds.
DEBUG:app.py:Read 1667163 bytes, wrote 1116999 bytes, compression ratio was 67%
DEBUG:app.py:Currently using 70 MB
```

Providing you use a file name that does not already exist, your client can periodically poll the target file name until it is available. Here's a minimal example of how to do so using the AWS SDK for Python, [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html).

```python
s3_client = boto3.client('s3')

while True:
    try:
        # Get information on the object
        s3_client.head_object(
            Bucket=bucket,
            Key=key
        )
        print(f'{bucket}/{key} is available')
        break
    except ClientError as err:
        if err.response['ResponseMetadata']['HTTPStatusCode'] == 404:
            # The object was not found - sleep for a second then try again
            time.sleep(1)
        else:
            # Some other problem!
            raise err
```

## Going Further

Feel free to fork this repository and use it as a starting point for your own app. Let us know
at evangelism@backblaze.com if you come up with something interesting!
