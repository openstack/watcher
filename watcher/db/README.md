# Watcher Database

This database stores all the watcher business objects which can be requested by the Watcher API :
* Audit templates
* Audits
* Action plans
* Actions history
* Watcher settings :
  * metrics/events collector endpoints for each type of metric
  * manual/automatic mode
* Business Objects states

It may be any relational database or a key-value database.

Business objects are read/created/updated/deleted from/to the Watcher database using a common Python package which provides a high-level Service API.
