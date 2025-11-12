#!/usr/bin/env python3
"""
Загружает список всех криптовалют с логотипами с CoinGecko
и сохраняет в JSON файл data/cryptos.json

ЗАПУСТИТЬ ОДИН РАЗ:
    python scripts/init_cryptos.py
"""

import asyncio
import httpx
import json
from pathlib import Path
import sys

DATA_DIR = Path('data')
CRYPTOS_FILE = DATA_DIR / 'cryptos.json'


async def download_all_cryptos():
    """Загружает список всех криптовалют и сохраняет в JSON"""

    print("\n" + "=" * 70)
    print("🚀 ЗАГРУЗКА ВСЕХ КРИПТОВАЛЮТ С ЛОГОТИПАМИ")
    print("=" * 70 + "\n")

    try:
        print("📥 Подключаемся к CoinGecko API...")

        async with httpx.AsyncClient(timeout=30) as client:
            # Загружаем список всех криптовалют
            response = await client.get(
                'https://api.coingecko.com/api/v3/coins/list',
                headers={'User-Agent': 'CryptoBot/1.0'}
            )

            if response.status_code == 200:
                coins_list = response.json()
                print(f"✅ Получено {len(coins_list)} криптовалют\n")

                # Преобразуем в удобный формат
                cryptos = {}

                print("🔄 Преобразую данные...")

                for i, coin in enumerate(coins_list):
                    symbol = coin.get('symbol', '').upper()
                    coin_id = coin.get('id', '')
                    name = coin.get('name', '')

                    if symbol and coin_id:
                        # URL на GitHub иконки (очень быстрый CDN)
                        logo_url = f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{symbol.lower()}.png"

                        cryptos[symbol] = {
                            'symbol': symbol,
                            'name': name,
                            'id': coin_id,
                            'logo': logo_url
                        }

                    # Прогресс
                    if (i + 1) % 1000 == 0:
                        print(f"  ✓ Обработано {i + 1} криптовалют...")

                # Создаём директорию если её нет
                DATA_DIR.mkdir(exist_ok=True)

                # Сохраняем в JSON
                print("\n💾 Сохраняю в JSON файл...")
                with open(CRYPTOS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cryptos, f, indent=2, ensure_ascii=False)

                file_size = CRYPTOS_FILE.stat().st_size / 1024 / 1024

                print("\n" + "=" * 70)
                print("✅ УСПЕШНО!")
                print("=" * 70)
                print(f"📊 Сохранено {len(cryptos)} криптовалют")
                print(f"📁 Файл: {CRYPTOS_FILE.absolute()}")
                print(f"💾 Размер: {file_size:.2f} MB")
                print("\n✅ Готово! Теперь запусти приложение:")
                print("   python -m uvicorn api.web_app_api:app\n")
                print("=" * 70 + "\n")

                return True

            elif response.status_code == 429:
                print("❌ 429 Too Many Requests")
                print("\nСервер CoinGecko переполнен. Попробуй позже.\n")
                return False

            else:
                print(f"❌ Ошибка API: {response.status_code}\n")
                return False

    except Exception as e:
        print(f"❌ Ошибка: {e}\n")
        return False


async def main():
    success = await download_all_cryptos()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())