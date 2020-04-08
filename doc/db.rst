Database functions
==================

Simple thread-safe SQLAlchemy wrapper

after initialization, wrapper object contains additional params:

* **use_lastrowid** show last row id be used (sqlite, mysql)

* **use_interval** can interval columns be used (not available for sqlite,
  mysql)

* **parse_db_json** should JSON column be parsed after selecting (sqlite,
  mysql)

.. automodule:: pyaltt2.db
   :members:
