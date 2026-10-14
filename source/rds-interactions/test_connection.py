from db import get_connection


def main() -> None:
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    VERSION() AS version,
                    CURRENT_USER() AS authenticated_user,
                    DATABASE() AS current_database
                """
            )
            print(cursor.fetchone())
    finally:
        connection.close()


if __name__ == "__main__":
    main()