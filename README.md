# IMDb Media Catalog

This project provides scripts to download and process IMDb datasets to create an offline media catalog for autosuggest functionality.

## Scripts

- `01_download_imdb.py`: Downloads the required IMDb bulk datasets (title.basics.tsv.gz and title.ratings.tsv.gz).
- `02_create_catalog.py`: Processes the datasets to generate media_catalog.csv containing movies and TV series with ratings and votes, sorted by popularity.
- `03_filter_catalog.py`: Filters the catalog to include only entries with a minimum number of votes.
