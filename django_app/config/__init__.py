# Use PyMySQL as the MySQL driver (pure Python, no C compiler needed on Windows/macOS).
import pymysql

pymysql.version_info = (1, 4, 6, "final", 0)  # satisfy Django's mysqlclient version check
pymysql.install_as_MySQLdb()
