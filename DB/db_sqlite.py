import sqlite3 as sq


class DataBase:
    def __init__(self):
        self.connect = sq.connect("DB/bot_database.db")
        self.cursor = self.connect.cursor()
        if self.connect:
            print("Data base connected OK!")
            self.create_scheme()

    def create_scheme(self):
        """Создание схемы таблиц в БД"""
        with self.connect as connect:
            try:
                connect.execute(
                    f"""CREATE TABLE users (user_id	INTEGER NOT NULL UNIQUE)"""
                )
                connect.commit()
            except Exception as e:
                print(f"При создании таблицы БД возникло исключение: {e}")

            try:
                connect.execute(
                    f"""CREATE TABLE positions (articul	INTEGER NOT NULL,
                                                            name TEXT,
                                                            price INTEGER,
                                                            img BLOB,
                                                            user_id INTEGER,
                                                            date_time INTEGER,
                                                            source TEXT)"""
                )
                connect.commit()
            except Exception as e:
                print(f"При создании таблицы БД возникло исключение: {e}")

    async def save_client(self, user_id):
        with self.connect as connect:
            connect.execute(f"""INSERT INTO users (user_id) VALUES ({user_id})""")
            connect.commit()

    async def check_user(self, user_id):
        with self.connect as connect:
            result = bool(
                connect.execute(
                    f""" SELECT user_id FROM users WHERE user_id = {user_id} """
                ).fetchone()
            )
        return result

    def all_users(self):
        """Не асинхронная потому что вызывается однократно при старте бота"""
        with self.connect as connect:
            result = connect.execute(f""" SELECT user_id FROM users """).fetchall()
        return [int(x[0]) for x in result] if len(result) != 0 else []

    async def get_all_users(self):
        """Не асинхронная потому что вызывается однократно при старте бота"""
        with self.connect as connect:
            result = connect.execute(f""" SELECT user_id FROM users """).fetchall()
        return [int(x[0]) for x in result] if len(result) != 0 else []

    async def save_position(
        self, articul, name, price, date_time, user_id, img, source
    ):
        with self.connect as connect:
            connect.execute(
                f"INSERT INTO positions (articul, name, price, img, user_id, date_time, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (articul, name, price, img, user_id, date_time, source),
            )
            connect.commit()

    async def check_position(self, articul, user_id, source):
        with self.connect as connect:
            result = bool(
                connect.execute(
                    f""" SELECT articul FROM positions WHERE articul = {articul} AND user_id = {user_id} AND source = '{source}'"""
                ).fetchone()
            )
        return result

    async def get_all_position(self, user_id, source):
        with self.connect as connect:
            result = connect.execute(
                f""" SELECT * FROM positions WHERE user_id = {user_id} AND source = '{source}' """
            ).fetchall()
        return result

    async def dell_position(self, articul, user_id, source):
        with self.connect as connect:
            connect.execute(
                f"""DELETE FROM positions WHERE articul = {articul} AND user_id = {user_id} AND source = '{source}'"""
            )
            connect.commit()

    async def update_price(self, articul, user_id, price, source):
        with self.connect as connect:
            connect.execute(
                f"""UPDATE positions SET price = '{price}' WHERE articul = {articul} AND user_id = {user_id} AND source = '{source}'"""
            )
            connect.commit()
