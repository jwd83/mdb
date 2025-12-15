import subprocess

urls = [
    "https://datasets.imdbws.com/title.basics.tsv.gz",
    "https://datasets.imdbws.com/title.ratings.tsv.gz"
]

# Run curl commands to download the files
for url in urls:
       subprocess.run(["curl", "-O", url])
