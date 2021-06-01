
# pyAstroRef


An astronomy focused reference manager which integrates with adsabs and the arxiv.


## Installation


Follow the instructions to install gtk and pygobject from https://pygobject.readthedocs.io/en/latest/getting_started.html

Install dependices:

```
pip install -r requirements.txt
```

Build and install software

```
pip install .
```

And run
```
pyastroref
```

## Documentation

Documentation can be found at https://pyastroref.readthedocs.io/en/latest/


## ADS Key

You will need your own ADS api key: https://ui.adsabs.harvard.edu/user/settings/token

This can either be saved to the file:
```
~/.ads/dev_key
```

Or it can be set in the options menu.

Note after changing (or setting) your ads_key you will need to restart pyAstroRef.

## Acknowledgements

This research has made use of NASA’s Astrophysics Data System Bibliographic Services.
Thank you to arXiv for use of its open access interoperability.
