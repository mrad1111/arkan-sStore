# MySQL Configuration Guide

This project is configured exclusively to use **MySQL**.

## Configuration

1. Make sure your MySQL Server (XAMPP, WAMP, MySQL Workbench, Docker, or Cloud MySQL/Aiven/PlanetScale) is running.
2. Edit the `.env` file in the project root with your MySQL credentials:
   ```ini
   MYSQL_DATABASE=arkan_store
   MYSQL_USER=root
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3307
   ```
3. Run Django migrations to initialize your MySQL database schema:
   ```powershell
   py manage.py migrate
   ```
4. Start your Django server:
   ```powershell
   py manage.py runserver
   ```

---

## Vercel Deployment Note
Vercel serverless environments do not contain native MySQL C libraries (`mysqlclient`).
This project uses **PyMySQL** (`pymysql.install_as_MySQLdb()`) which is pure Python and compiles cleanly on Vercel without build errors.