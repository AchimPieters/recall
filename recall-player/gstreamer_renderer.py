import subprocess

def play(file):

    pipeline=[
    "gst-launch-1.0",
    "filesrc","location="+file,
    "!","decodebin",
    "!","autovideosink"
    ]

    subprocess.run(pipeline)
