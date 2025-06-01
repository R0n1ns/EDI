import webview
import argparse
import sys
# import webbrowser


def parse_arguments():
    parser = argparse.ArgumentParser(description='Docchat')
    parser.add_argument('--url', default='http://localhost:8000',
                        help='URL Django-сервера (по умолчанию: http://localhost:8000)')
    return parser.parse_args()


def create_window(url):
    # Конфигурация окна
    window = webview.create_window(
        title='Docchat',
        url=url,
        width=1200,
        height=800,
        resizable=True,
        text_select=True,
        confirm_close=True
    )

    # Обработчики событий
    window.events.closed += lambda: sys.exit(0)
    # window.events.loaded += lambda: print("Приложение загружено")

    return window


def main():
    args = parse_arguments()
    server_url = args.url

    print(f"Подключение к Docchat-серверу: {server_url}")
    print("Для выхода нажмите Ctrl+C в консоли или закройте окно")

    # # Проверка доступности сервера (опционально)
    # try:
    #     webbrowser.open(server_url)  # Тестовое открытие в браузере
    # except Exception as e:
    #     print(f"Ошибка подключения: {e}")
    #     print("Убедитесь что Django-сервер запущен и доступен")

    # Создание и запуск окна
    window = create_window(server_url)
    webview.start(
        gui='qt',  # Используем Qt для лучшей совместимости
        # debug=True,  # Режим отладки
        http_server=False,
        private_mode=False
    )


if __name__ == '__main__':
    main()
