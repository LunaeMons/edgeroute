"""EdgeRoute: the multi-CDN steering service for Northwind Media.

The package is organised by feature. Each feature folder holds its HTTP endpoints
(``router.py``) and its logic. Depending on what the feature needs, it also has
request and response models (``schemas.py``), database tables (``models.py``) and
database access (``repository.py``):

* ``app.cdns``: register and manage the CDN providers.
* ``app.steering``: decide which CDN a video player should use.
* ``app.probes``: import probe measurements and compute CDN health.

Shared plumbing lives at the top level: ``config`` (settings), ``db`` (SQLite),
``auth`` (the admin token check) and ``main`` (the application factory).
"""
