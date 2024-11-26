import socket
import threading
import time

# Глобальные переменные
cities = set()  # Хранит использованные города
last_city = None
game_over = False
turn_condition = threading.Condition()  # Управление очередностью ходов
timeout = 20  # Таймаут на ввод (d секундах)
turn = 0
clients = []

def check_city(city):
    """Проверяет правильность города."""
    global last_city, cities
    city = city.strip().lower()
    if city == '':
        return False, "Напишите название города."
    if city in cities:
        return False, "Этот город уже был назван."
    if last_city and city[0] != last_city[-1]:
        return False, f"Город должен начинаться на '{last_city[-1].upper()}'."
    return True, None


def handle_client(client, opponent, idx):
    """Обрабатывает клиента."""
    global last_city, game_over, turn

    while not game_over:
        with turn_condition:
            while not (turn == idx):  # Ждем своей очереди
                turn_condition.wait()

            try:
                # Уведомить клиента о его ходе
                client.send("Ваш ход: ".encode("utf-8"))
                # Запустить таймер
                client.settimeout(timeout)
                try:
                    city = client.recv(1024).decode("utf-8").strip()
                except socket.timeout:
                    client.send("Вы не ответили вовремя! Игра окончена.\n".encode("utf-8"))
                    opponent.send("Ваш соперник не ответил вовремя! Вы победили!\n".encode("utf-8"))
                    game_over = True
                    return

                # Проверить город
                valid, message = check_city(city)
                if not valid:
                    client.send(f"Ошибка: {message}\n".encode("utf-8"))
                    continue

                # Если город правильный, обновить состояние игры
                last_city = city
                cities.add(city)
                opponent.send(f"Ваш соперник назвал город: {city}\n".encode("utf-8"))

            except Exception as e:
                print(f"Ошибка: {e}")
                break

            # Передать ход другому игроку
            turn = (turn + 1) % len(clients)
            turn_condition.notify()

def main():
    """Основной сервер."""
    global game_over

    host = "127.0.0.1"
    port = 12346
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(2)

    print("Ожидание двух игроков для начала игры...")

    # Подключить двух клиентов
    while len(clients) < 2:
        client, addr = server.accept()
        print(f"Игрок подключился: {addr}")
        client.send("Вы подключились к игре d города! Ожидаем второго игрока...\n".encode("utf-8"))
        clients.append(client)

    # Уведомить игроков о начале игры
    for client in clients:
        client.send("Оба игрока подключены. Игра начинается!\n".encode("utf-8"))

    # Запустить обработку для каждого клиента
    threads = []
    threads.append(threading.Thread(target=handle_client, args=(clients[0], clients[1], 0)))
    threads.append(threading.Thread(target=handle_client, args=(clients[1], clients[0], 1)))

    for thread in threads:
        thread.start()

    # Ожидать завершения игры
    for thread in threads:
        thread.join()

    # Закрыть соединения
    for client in clients:
        client.close()
    server.close()

if __name__ == "__main__":
    main()
