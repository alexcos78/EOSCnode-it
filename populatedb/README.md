#Import services into the EOSCnode MariaDB schema from a CSV exported from the provided Excel template.

##Usage:
```shell script
  python3 import_services.py --csv services.csv --db eoscnode --user eoscnode --password 'PASSWORD'
```

##Dependencies on Debian:
```shell script
  sudo apt install python3-pymysql
```
